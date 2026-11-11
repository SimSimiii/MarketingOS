"""Proposals to edit a finished email: create, decide, keep the history.

Shaped like the email-analysis job beside it: the request thread validates
and writes a row, a background task buys the bounded writer passes, and the
page polls the row. The asset itself only changes when the user accepts a
proposal - and then the original is kept on the asset, so "restore original"
is a copy rather than a guess.
"""

import asyncio
import logging
from datetime import UTC, datetime
from threading import RLock
from uuid import UUID

from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.ai.base import AIProvider
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR, get_settings
from app.knowledge.ledger import EvidenceIndex
from app.marketing.briefs import CampaignBrief, EmailBrief
from app.marketing.craft import check_draft
from app.marketing.email_copy import Email, render_review
from app.marketing.gates import GateReport
from app.marketing.grounding import ClaimReviewer, reuse_review, review_key
from app.marketing.intent import CampaignIntent
from app.marketing.policy import resolve_policy
from app.marketing.request import CampaignRequest
from app.marketing.revision import (
    MAX_INSTRUCTION_CHARS,
    MAX_REVISIONS_PER_EMAIL,
    adjust_email,
    adjustment_review_brief,
)
from app.marketing.steering import CampaignSteering
from app.marketing.writer import EmailWriter
from app.models.campaign import Campaign
from app.models.campaign_execution import CampaignExecution
from app.models.email_revision import EmailRevision
from app.models.enums import AssetType, ExecutionStatus
from app.models.generated_asset import GeneratedAsset
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession, RoleCall
from app.runtime.prompt_engine import get_prompt_engine
from app.runtime.work_limits import admitted_job, create_job_task

logger = logging.getLogger(__name__)
_tasks: set[asyncio.Task] = set()
_selection_lock = RLock()
#: The two writer passes, with room for their format repairs. A proposal that
#: has not come back by then is reported as failed, never left spinning.
_TIMEOUT_SECONDS = 420

#: Fields of the asset that describe one version of the email, as opposed to
#: what the run measured about it.
_VERSION_KEYS = ("title", "content", "content_html")


class RevisionError(ValueError):
    def __init__(self, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.status_code = status_code


# ------------------------------------------------------------------ reads


def history(db: Session, asset: GeneratedAsset) -> list[EmailRevision]:
    return list(db.exec(
        select(EmailRevision).where(EmailRevision.asset_id == asset.id)
        .order_by(col(EmailRevision.created_at))
    ))


def original_of(asset: GeneratedAsset) -> dict:
    """The version the run delivered, whichever version is selected now."""
    meta = asset.asset_metadata or {}
    if isinstance(meta.get("original"), dict):
        return meta["original"]
    return {"title": asset.title, "content": asset.content, "content_html": asset.content_html}


def selected_revision_id(asset: GeneratedAsset) -> str | None:
    return (asset.asset_metadata or {}).get("selected_revision_id")


# --------------------------------------------------------------- creating


def validate(
    db: Session, execution: CampaignExecution, asset: GeneratedAsset,
    instruction: str, base_revision_id: UUID | None,
) -> EmailRevision | None:
    if get_settings().credit_billing_enabled:
        raise RevisionError("Editing an email with the model is unavailable in credit billing mode.")
    if asset.campaign_execution_id != execution.id:
        raise RevisionError("Email not found", 404)
    if asset.asset_type is not AssetType.EMAIL:
        raise RevisionError("Only emails can be adjusted this way.")
    if execution.status is not ExecutionStatus.COMPLETED:
        raise RevisionError("Wait for the run to finish before adjusting its emails.")
    if not instruction.strip():
        raise RevisionError("Say what should change.", 422)
    if len(instruction) > MAX_INSTRUCTION_CHARS:
        raise RevisionError(f"Keep the request under {MAX_INSTRUCTION_CHARS} characters.", 422)
    if not _stored_brief(execution, asset):
        raise RevisionError("This run kept no plan for this email, so it cannot be adjusted safely.")
    if len(history(db, asset)) >= MAX_REVISIONS_PER_EMAIL:
        raise RevisionError(
            f"This email reached its limit of {MAX_REVISIONS_PER_EMAIL} proposals. "
            "Edit it by hand, or duplicate the campaign and run it again."
        )
    if base_revision_id is None:
        return None
    base = db.get(EmailRevision, base_revision_id)
    if base is None or base.asset_id != asset.id or base.email is None:
        raise RevisionError("The version to adjust no longer exists.", 404)
    return base


@admitted_job
def launch(
    db: Session, campaign: Campaign, execution: CampaignExecution, asset: GeneratedAsset,
    provider: AIProvider, instruction: str, base_revision_id: UUID | None = None,
) -> EmailRevision:
    """Record the request and start the bounded writer job."""
    instruction = " ".join(instruction.split())
    validate(db, execution, asset, instruction, base_revision_id)
    row = EmailRevision(
        asset_id=asset.id, campaign_execution_id=execution.id,
        base_revision_id=base_revision_id, instruction=instruction,
        active_key=str(asset.id),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise RevisionError("A proposal for this email is already being written.") from exc
    db.refresh(row)
    task = create_job_task(run_job(db.get_bind(), row.id, provider))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return row


def _stored_brief(execution: CampaignExecution, asset: GeneratedAsset) -> EmailBrief | None:
    """The slot as it was finally written, falling back to the plan.

    Newer assets carry the brief after any pivot; older ones only have the
    run's plan, which is the same slot before the loop changed its idea.
    """
    selected = (asset.asset_metadata or {}).get("selected_brief")
    if isinstance(selected, dict):
        return EmailBrief.model_validate(selected)
    plan = (execution.result or {}).get("brief")
    if not isinstance(plan, dict):
        return None
    return CampaignBrief.model_validate(plan).brief_for(asset.position)


def _email_of(asset: GeneratedAsset) -> Email:
    return Email.model_validate({**(asset.asset_metadata or {}), "position": asset.position})


def _request_for(campaign: Campaign) -> CampaignRequest:
    return CampaignRequest(
        name=campaign.name, request=campaign.request,
        product_description=campaign.product_description, product_url=campaign.product_url,
        target_market=campaign.target_market, goals=campaign.goals,
        intent=CampaignIntent.model_validate(campaign.intent) if campaign.intent else None,
        sender_name=campaign.sender_name or "", sender_role=campaign.sender_role or "",
        cta_url=campaign.cta_url,
        steering=CampaignSteering.model_validate(campaign.steering) if campaign.steering else None,
    )


async def run_job(engine: Engine, revision_id: UUID, provider: AIProvider) -> None:
    from app.orchestration.campaign_orchestrator import (
        CampaignOrchestrator,
        _DbKnowledgeGateway,
        _resolve_overrides,
    )

    with Session(engine) as db:
        row = db.get(EmailRevision, revision_id)
        if row is None or row.state != "running":
            return

        def record(call: RoleCall) -> None:
            row.calls += 1
            row.input_tokens += call.billable_input_tokens
            row.output_tokens += call.output_tokens
            db.add(row)
            db.commit()

        try:
            asset = db.get(GeneratedAsset, row.asset_id)
            execution = db.get(CampaignExecution, row.campaign_execution_id)
            campaign = db.get(Campaign, execution.campaign_id) if execution else None
            if asset is None or execution is None or campaign is None:
                raise RevisionError("The email or its campaign no longer exists.")
            brief = _stored_brief(execution, asset)
            plan = CampaignBrief.model_validate((execution.result or {}).get("brief") or {})
            if brief is None:
                raise RevisionError("This run kept no plan for this email.")
            base = db.get(EmailRevision, row.base_revision_id) if row.base_revision_id else None
            draft = (Email.model_validate(base.email) if base is not None and base.email
                     else Email.model_validate({**_email_of(asset).model_dump(),
                                                **_original_email(asset)}))
            earlier = _chain(db, base)
            gateway = _DbKnowledgeGateway(db, campaign)
            stored = gateway.load()
            if stored is None:
                raise RevisionError("This campaign's knowledge is no longer available.")
            if gateway.fingerprint() != stored.fingerprint:
                raise RevisionError("The sources changed. Recompile them before requesting an AI adjustment.")
            artifacts = stored.artifacts
            siblings = db.exec(select(GeneratedAsset).where(
                GeneratedAsset.campaign_execution_id == execution.id,
                GeneratedAsset.asset_type == AssetType.EMAIL,
                GeneratedAsset.id != asset.id,
            )).all()
            previous = [_email_of(item) for item in sorted(siblings, key=lambda a: a.position)]
            policy = resolve_policy(
                (campaign.policy or {}).get("preset"),
                {k: v for k, v in (campaign.policy or {}).items() if k != "preset"} or None,
            )
            session = ModelSession(
                provider, get_prompt_engine(PROMPTS_DIR), EventBus(),
                ModelRouter(_resolve_overrides(policy, campaign)),
                f"email-revision:{row.id}", on_call=record,
            )
            async with asyncio.timeout(_TIMEOUT_SECONDS):
                corpus = gateway.corpus()
                # Older assets predate AI source receipts. Review their original
                # once so accepting a new proposal does not make restoration
                # impossible. This approval never validates the new proposal.
                meta = dict(asset.asset_metadata or {})
                original = meta.get("original")
                original_email = Email.model_validate(
                    original["email"] if isinstance(original, dict) else _email_of(asset).model_dump()
                )
                original_receipt = (original.get("semantic_review") if isinstance(original, dict)
                                    else meta.get("semantic_review"))
                if (not original_receipt
                        or original_receipt.get("key") != review_key(original_email, brief, artifacts)):
                    original_checks = await ClaimReviewer(session).review(
                        email=original_email, brief=brief, artifacts=artifacts, hints=GateReport(),
                        corpus=corpus,
                    )
                    if isinstance(original, dict):
                        meta["original"] = {**original, "semantic_review": original_checks.semantic_review}
                    else:
                        meta["semantic_review"] = original_checks.semantic_review
                    asset.asset_metadata = meta
                    db.add(asset)
                    db.commit()
                adjustment = await adjust_email(
                    writer=EmailWriter(session, corpus=corpus), draft=draft, brief=brief, campaign=plan,
                    request=_request_for(campaign), artifacts=artifacts,
                    evidence=EvidenceIndex(artifacts.evidence, corpus.text),
                    previous=previous, instruction=row.instruction, earlier_requests=earlier,
                    merge_fields=policy.merge_fields, positioning=gateway.positioning(),
                )
            content, content_html, _ = CampaignOrchestrator(db, provider).render_email(
                campaign, adjustment.email, brief, artifacts
            )
            row.email = adjustment.email.model_dump(mode="json")
            row.content, row.content_html = content, content_html
            row.checks = adjustment.gates.model_dump(mode="json")
            row.attempts = adjustment.passes
            row.state = "blocked" if adjustment.blocked else "proposed"
            if not adjustment.blocked and _same_copy(adjustment.email, draft):
                # Seen live: asked to add a figure the material does not hold,
                # the writer rightly changed nothing - and the page offered an
                # identical "proposal" to accept with no word about why.
                row.state = "unchanged"
                row.error = (
                    "No change was made. The request could not be met without a claim, "
                    "price or fact this email is not allowed to use, so the email was left "
                    "as it was."
                )
        except asyncio.CancelledError:
            row.state, row.error = "failed", "The proposal was interrupted. Ask again."
            raise
        except RevisionError as exc:
            row.state, row.error = "failed", str(exc)
        except TimeoutError:
            row.state, row.error = "failed", "The proposal took too long. Ask again."
        except Exception:
            logger.exception("Email revision %s failed", row.id)
            row.state = "failed"
            row.error = "The proposal could not be written. The email is unchanged."
        finally:
            row.active_key = None
            row.completed_at = datetime.now(UTC)
            db.add(row)
            db.commit()


def _same_copy(left: Email, right: Email) -> bool:
    """Identical authored copy; changed spelling or typography is still a proposal."""
    def key(email: Email) -> str:
        return render_review(email)
    return key(left) == key(right)


def _original_email(asset: GeneratedAsset) -> dict:
    original = (asset.asset_metadata or {}).get("original")
    return original.get("email", {}) if isinstance(original, dict) else {}


def _chain(db: Session, base: EmailRevision | None) -> list[str]:
    """What the user already asked for on the version being adjusted."""
    asked: list[str] = []
    seen: set[UUID] = set()
    while base is not None and base.id not in seen:
        seen.add(base.id)
        asked.append(base.instruction)
        base = db.get(EmailRevision, base.base_revision_id) if base.base_revision_id else None
    return list(reversed(asked))


# --------------------------------------------------------------- deciding


def _own(db: Session, asset: GeneratedAsset, revision_id: UUID) -> EmailRevision:
    row = db.get(EmailRevision, revision_id)
    if row is None or row.asset_id != asset.id:
        raise RevisionError("Proposal not found", 404)
    return row


def accept(db: Session, asset: GeneratedAsset, revision_id: UUID) -> GeneratedAsset:
    with _selection_lock:
        db.refresh(asset)
        return _accept_checked(db, asset, revision_id)


def _check_selection(db: Session, asset: GeneratedAsset, email: Email,
                     receipt: dict | None = None, instruction: str = "",
                     earlier_requests: list[str] | None = None) -> GateReport:
    """Other chosen versions may have changed since this proposal was written."""
    from app.orchestration.campaign_orchestrator import _DbKnowledgeGateway

    execution = db.get(CampaignExecution, asset.campaign_execution_id)
    campaign = db.get(Campaign, execution.campaign_id) if execution else None
    if execution is None or campaign is None:
        raise RevisionError("The email or its campaign no longer exists.")
    brief = _stored_brief(execution, asset)
    gateway = _DbKnowledgeGateway(db, campaign)
    stored = gateway.load()
    if brief is None or stored is None:
        raise RevisionError("The plan or knowledge needed to check this version is unavailable.")
    review_brief = adjustment_review_brief(brief, instruction, earlier_requests) if instruction else brief
    siblings = db.exec(select(GeneratedAsset).where(
        GeneratedAsset.campaign_execution_id == execution.id,
        GeneratedAsset.asset_type == AssetType.EMAIL,
        GeneratedAsset.id != asset.id,
    )).all()
    policy = resolve_policy(
        (campaign.policy or {}).get("preset"),
        {k: v for k, v in (campaign.policy or {}).items() if k != "preset"} or None,
    )
    report, _ = check_draft(
        email, brief, artifacts=stored.artifacts,
        evidence=EvidenceIndex(stored.artifacts.evidence, gateway.corpus().text),
        previous=[_email_of(item) for item in sorted(siblings, key=lambda a: a.position)],
        merge_fields=policy.merge_fields, positioning=gateway.positioning(),
    )
    if gateway.fingerprint() != stored.fingerprint:
        raise RevisionError("The sources changed. Recompile them and request a new AI review.")
    checked = reuse_review(report, receipt, email=email, brief=review_brief, artifacts=stored.artifacts)
    if checked.blocking and receipt and receipt.get("version") == 1:
        # Old campaign reviews included the researched audience in their key;
        # reconstruct it rather than treating a layout/view change as new facts.
        bundle = gateway.campaign_intelligence(stored.artifacts)
        if bundle is not None:
            checked = reuse_review(report, receipt, email=email, brief=review_brief, artifacts=bundle.artifacts)
    return checked


def _accept_checked(db: Session, asset: GeneratedAsset, revision_id: UUID) -> GeneratedAsset:
    """Make a proposal the version that is copied and exported.

    A blocked proposal cannot be chosen: the user's preference decides what
    the email says, never whether an unsupported claim ships.
    """
    row = _own(db, asset, revision_id)
    if row.state not in {"proposed", "accepted", "rejected"} or row.email is None:
        raise RevisionError(
            "This proposal failed an automatic check and cannot be used."
            if row.state == "blocked" else "This proposal is not ready to use."
        )
    report = _check_selection(db, asset, Email.model_validate(row.email),
                              (row.checks or {}).get("semantic_review"), row.instruction,
                              _chain(db, db.get(EmailRevision, row.base_revision_id) if row.base_revision_id else None))
    row.checks = report.model_dump(mode="json")
    if report.blocking:
        row.error = "This version fails the current automatic checks. Ask for another adjustment."
        if row.state != "accepted":
            row.state = "blocked"
        db.add(row)
        db.commit()
        raise RevisionError(row.error)
    row.error = ""
    meta = dict(asset.asset_metadata or {})
    if "original" not in meta:
        meta["original"] = {
            **{key: getattr(asset, key) for key in _VERSION_KEYS},
            "email": _email_of(asset).model_dump(mode="json"),
            "pull": meta.get("pull"),
            "semantic_review": meta.get("semantic_review"),
        }
    meta.update(row.email)
    # The run's cold-read score was earned by other words. Carried over, it
    # would tell the user an unread edit had been measured.
    meta.update({"pull": None, "selected_revision_id": str(row.id), "edited": True,
                 "semantic_review": report.semantic_review})
    asset.title = row.email.get("subject") or asset.title
    asset.content, asset.content_html = row.content, row.content_html
    asset.asset_metadata = meta
    row.state, row.decided_at = "accepted", datetime.now(UTC)
    db.add(row)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def reject(db: Session, asset: GeneratedAsset, revision_id: UUID) -> EmailRevision:
    row = _own(db, asset, revision_id)
    if row.state not in {"proposed", "blocked"}:
        raise RevisionError("Only a pending proposal can be declined.")
    row.state, row.decided_at = "rejected", datetime.now(UTC)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def restore_original(db: Session, asset: GeneratedAsset) -> GeneratedAsset:
    with _selection_lock:
        db.refresh(asset)
        return _restore_original_checked(db, asset)


def _restore_original_checked(db: Session, asset: GeneratedAsset) -> GeneratedAsset:
    meta = dict(asset.asset_metadata or {})
    original = meta.get("original")
    if not isinstance(original, dict):
        return asset
    report = _check_selection(db, asset, Email.model_validate(original.get("email") or {}),
                              original.get("semantic_review"))
    if report.blocking:
        raise RevisionError("The original fails the current automatic checks and cannot be selected.")
    for key in _VERSION_KEYS:
        setattr(asset, key, original.get(key))
    meta.update(original.get("email") or {})
    meta.update({"pull": original.get("pull"), "selected_revision_id": None, "edited": False,
                 "semantic_review": report.semantic_review})
    asset.asset_metadata = meta
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def reap_email_revisions(engine: Engine) -> None:
    with Session(engine) as db:
        for row in db.exec(select(EmailRevision).where(EmailRevision.state == "running")):
            row.state, row.active_key = "failed", None
            row.error = "Server restarted before the proposal finished. Ask again."
            row.completed_at = datetime.now(UTC)
            db.add(row)
        db.commit()
