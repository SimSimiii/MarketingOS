"""Evaluate finished email campaigns without changing or publishing them.

Examples (run from ``backend``)::

    python -m app.evaluation.campaign_quality_bench \
      --campaign strong-grounded --out eval/campaign-quality

    python -m app.evaluation.campaign_quality_bench \
      --campaign <campaign-uuid> --out eval/campaign-quality --live

``--campaign`` is repeatable and accepts a built-in fixture name, a fixture
JSON path, or a campaign UUID from the configured application database.  The
default run is deterministic and spends no model quota.  ``--live`` is the
only path that constructs a model provider and it prints the expected number
of calls before starting.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError
from sqlmodel import Session, select

from app.ai.factory import get_ai_provider
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR
from app.core.database import engine
from app.evaluation.campaign_quality import (
    CampaignDraft,
    CampaignQualityCase,
    CampaignQualityContext,
    CampaignQualityReport,
    CommercialReviewer,
    EvidenceReference,
    EvidenceScope,
    ForbiddenClaim,
    evaluate_campaign,
)
from app.evaluation.head_to_head import assessor_panel
from app.knowledge.artifacts import Grounding, KnowledgeArtifacts
from app.market.relevance import ClaimContract
from app.marketing.briefs import CampaignBrief
from app.marketing.email_copy import Email, EmailCopyError, parse_email
from app.models.campaign import Campaign
from app.models.generated_asset import GeneratedAsset
from app.models.knowledge_artifacts import KnowledgeArtifactSet
from app.repositories.campaign_execution_repository import CampaignExecutionRepository
from app.repositories.generated_asset_repository import GeneratedAssetRepository
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import get_prompt_engine
from app.schemas.campaign import CampaignGenerationAdvice

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "eval" / "fixtures" / "campaign_quality"


class CampaignQualityLoadError(ValueError):
    pass


def load_case(reference: str) -> CampaignQualityCase:
    """Load one immutable evaluation input from a fixture or the database."""

    path = Path(reference)
    if path.is_file():
        return _load_fixture(path)
    fixture = FIXTURE_DIR / f"{reference}.json"
    if fixture.is_file():
        return _load_fixture(fixture)
    try:
        campaign_id = UUID(reference)
    except ValueError as exc:
        available = ", ".join(path.stem for path in sorted(FIXTURE_DIR.glob("*.json")))
        raise CampaignQualityLoadError(
            f"{reference!r} is not a fixture path, known fixture, or campaign UUID. "
            f"Known fixtures: {available or 'none'}"
        ) from exc
    return _load_database_campaign(campaign_id)


def _load_fixture(path: Path) -> CampaignQualityCase:
    try:
        case = CampaignQualityCase.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CampaignQualityLoadError(f"could not load campaign fixture {path}: {exc}") from exc
    case.source = str(path.resolve())
    return case


def _load_database_campaign(campaign_id: UUID) -> CampaignQualityCase:
    with Session(engine) as session:
        campaign = session.get(Campaign, campaign_id)
        if campaign is None:
            raise CampaignQualityLoadError(f"campaign {campaign_id} does not exist")

        executions = CampaignExecutionRepository(session).list_by_campaign(campaign.id)
        chosen = None
        assets: list[GeneratedAsset] = []
        for execution in executions:
            candidate = sorted(
                GeneratedAssetRepository(session).list_by_execution(execution.id),
                key=lambda asset: asset.position,
            )
            candidate = [asset for asset in candidate if str(asset.asset_type) == "email"]
            if candidate:
                chosen, assets = execution, candidate
                break
        if chosen is None:
            raise CampaignQualityLoadError(
                f"campaign {campaign_id} has no generated email assets to evaluate"
            )

        result = chosen.result or {}
        brief = (
            CampaignBrief.model_validate(result["brief"])
            if isinstance(result.get("brief"), dict)
            else None
        )
        artifacts, artifact_note = _artifacts_for_run(session, campaign, result)
        advice, advice_note = _advice_for_run(chosen.recommendation_snapshot)
        context = _context_from_stored(campaign, brief, artifacts, advice)
        drafts: list[CampaignDraft] = []
        for asset in assets:
            email = _email_from_asset(asset)
            email_brief = brief.brief_for(email.position) if brief else None
            forbidden = [
                ForbiddenClaim(
                    id=f"BRIEF-{email.position}-MUST-NOT-{index}",
                    description=claim,
                )
                for index, claim in enumerate(
                    email_brief.must_not_say if email_brief else [], start=1
                )
                if claim.strip()
            ]
            drafts.append(CampaignDraft(id=str(asset.id), email=email, forbidden_claims=forbidden))

        notes = [
            "Database campaigns are evaluated read-only against their persisted final assets.",
        ]
        if artifact_note:
            notes.append(artifact_note)
        if advice_note:
            notes.append(advice_note)
        return CampaignQualityCase(
            id=str(campaign.id),
            name=campaign.name,
            context=context,
            drafts=drafts,
            source=f"database execution {chosen.id}",
            notes=notes,
        )


def _email_from_asset(asset: GeneratedAsset) -> Email:
    if asset.asset_metadata:
        try:
            return Email.model_validate(asset.asset_metadata)
        except ValidationError:
            pass
    try:
        return parse_email(asset.content, position=asset.position)
    except EmailCopyError as exc:
        raise CampaignQualityLoadError(
            f"generated asset {asset.id} is not a structured or parseable email: {exc}"
        ) from exc


def _artifacts_for_run(
    session: Session, campaign: Campaign, result: dict
) -> tuple[KnowledgeArtifacts | None, str]:
    version = int(result.get("knowledge_version") or 0)
    statement = select(KnowledgeArtifactSet)
    if campaign.brand_id is not None:
        statement = statement.where(KnowledgeArtifactSet.brand_id == campaign.brand_id)
    else:
        statement = statement.where(KnowledgeArtifactSet.campaign_id == campaign.id)
    if version:
        statement = statement.where(KnowledgeArtifactSet.version == version)
    statement = statement.order_by(KnowledgeArtifactSet.version.desc())
    row = session.exec(statement).first()
    if row is None or not row.payload:
        return None, (
            "The exact compiled knowledge used by this run was unavailable; safety checks "
            "therefore rely only on campaign inputs and fail closed on unsupported claims."
        )
    if version and row.version != version:
        return None, (
            f"Knowledge version {version} used by this run was unavailable; a newer version "
            "was not substituted because that would make the evaluation non-repeatable."
        )
    return KnowledgeArtifacts.model_validate(row.payload), ""


def _withheld_only_evidence(contract: ClaimContract | None) -> set[str]:
    """Ledger ids the contract withheld without also forbidding them.

    Empty for a legacy snapshot that predates the contract, where
    `forbidden_evidence_ids` did mean forbidden alone and every id in it is
    still a prohibition.
    """
    if contract is None:
        return set()
    forbidden = {
        evidence_id
        for claim in contract.forbidden_claims
        for evidence_id in claim.evidence_ids
    }
    withheld = {
        evidence_id
        for claim in contract.withheld_claims
        for evidence_id in claim.evidence_ids
    }
    return withheld - forbidden


def _context_from_stored(
    campaign: Campaign,
    brief: CampaignBrief | None,
    artifacts: KnowledgeArtifacts | None,
    advice: CampaignGenerationAdvice | None = None,
) -> CampaignQualityContext:
    all_evidence: list[EvidenceReference] = []
    contract: list[EvidenceReference] = []

    if artifacts is not None:
        all_evidence.extend(
            EvidenceReference(id=entry.id, text=entry.licensing_text)
            for entry in artifacts.evidence.entries
        )

    intelligence = (
        advice.recommendation if advice is not None and advice.recommendation is not None else None
    )
    v2_contract = intelligence is not None
    if v2_contract:
        allowed_ids = set(intelligence.allowed_evidence_ids)
        evidence = [item for item in all_evidence if item.id in allowed_ids]
        contract.extend(
            EvidenceReference(
                id=f"V2-ALLOWED-CLAIM-{index}",
                text=claim,
                scope=EvidenceScope.CAMPAIGN,
            )
            for index, claim in enumerate(intelligence.allowed_claims, start=1)
            if claim.strip()
        )
    else:
        evidence = all_evidence
        if campaign.product_description.strip():
            contract.append(
                EvidenceReference(
                    id="CAMPAIGN-PRODUCT-DESCRIPTION",
                    text=campaign.product_description,
                    scope=EvidenceScope.CAMPAIGN,
                )
            )
        if artifacts is not None and artifacts.business.what_it_does.strip():
            contract.append(
                EvidenceReference(
                    id="PROFILE-WHAT-IT-DOES",
                    text=artifacts.business.what_it_does,
                    scope=EvidenceScope.PRODUCT,
                )
            )
        if artifacts is not None:
            contract.extend(
                EvidenceReference(
                    id=f"PROFILE-FACT-{index}",
                    text=(
                        f"{fact.statement}\n{fact.provenance.quote}"
                        if fact.provenance and fact.provenance.quote
                        else fact.statement
                    ),
                    scope=EvidenceScope.PRODUCT,
                )
                for index, fact in enumerate(artifacts.business.facts, start=1)
                if fact.grounding in {Grounding.GROUNDED, Grounding.USER_STATED}
            )

    forbidden: list[ForbiddenClaim] = []
    if intelligence is not None:
        forbidden.extend(
            ForbiddenClaim(
                id=f"V2-FORBIDDEN-CLAIM-{index}",
                description=claim,
            )
            for index, claim in enumerate(intelligence.forbidden_claims, start=1)
            if claim.strip()
        )
        forbidden.extend(
            ForbiddenClaim(
                id=f"V2-CAPABILITY-{capability_id}",
                description=f"Capability {capability_id} is not verified for this product",
                patterns=_capability_patterns(capability_id),
            )
            for capability_id in intelligence.forbidden_capability_ids
            if capability_id.strip()
        )
        # `forbidden_evidence_ids` carries two different verdicts now that the
        # claim contract ships: evidence behind an unverified capability (a
        # lie) and evidence the dossier ranked WITHHOLD or contested (a fact
        # that may well be true and this campaign chose not to spend).  Only
        # the first is a forbidden claim.  Reporting a withheld fact as
        # forbidden is the exact collapse `ClaimContract` exists to prevent -
        # it tells the operator the product cannot do something it can.
        # Withheld evidence is already absent from `evidence` and `contract`
        # above, so CQ-SAF-004 and CQ-SAF-005 still fail closed on it under an
        # accurate rule.
        withheld_only = _withheld_only_evidence(intelligence.claim_contract)
        by_id = {item.id: item for item in all_evidence}
        forbidden.extend(
            ForbiddenClaim(
                id=f"V2-EVIDENCE-{evidence_id}",
                description=by_id[evidence_id].text,
            )
            for evidence_id in intelligence.forbidden_evidence_ids
            if evidence_id in by_id and evidence_id not in withheld_only
        )

    company_evidence: list[EvidenceReference] = []
    qualification = advice.selected_company_qualification if advice is not None else None
    if qualification is not None:
        from app.market.qualification import SignalGrounding

        company_evidence.extend(
            EvidenceReference(
                id=f"COMPANY-{signal.code or index}",
                text=f"{signal.code}={signal.value}. {signal.quote}",
                scope=EvidenceScope.COMPANY,
            )
            for index, signal in enumerate(qualification.evidence, start=1)
            if signal.grounding is SignalGrounding.DIRECT and signal.quote.strip()
        )

    product_name = artifacts.business.company_name if artifacts else ""
    target_audience = (
        brief.reader
        if brief and brief.reader
        else campaign.target_market or campaign.audience_segment or ""
    )
    personas = (
        assessor_panel(
            artifacts, brief.reader_segment if brief else campaign.audience_segment or ""
        )
        if artifacts is not None
        else ([target_audience] if target_audience else [])
    )
    return CampaignQualityContext(
        product_name=product_name,
        target_audience=target_audience,
        target_company=advice.selected_company_name if advice is not None else "",
        evidence=evidence,
        claim_contract=contract,
        claim_contract_enforced=v2_contract,
        company_evidence=company_evidence,
        forbidden_claims=forbidden,
        buyer_personas=personas,
    )


def _advice_for_run(
    payload: dict | None,
) -> tuple[CampaignGenerationAdvice | None, str]:
    if not payload:
        return None, (
            "No generation-time V2 recommendation snapshot was stored; legacy campaign and "
            "knowledge inputs define the claim boundary."
        )
    try:
        return CampaignGenerationAdvice.model_validate(payload), ""
    except ValidationError as exc:
        return None, (
            "The generation-time recommendation snapshot could not be read; it was not "
            f"replaced with current dossier state ({exc})."
        )


def _capability_patterns(capability_id: str) -> list[str]:
    normalized = capability_id.casefold().strip()
    known = {
        "voice_telephony": [
            (
                r"\b(?:support|offer|provide|handle|answer|make|take)s?\b.{0,24}"
                r"\b(?:voice|telephony|phone|calls?)\b"
            )
        ],
        "hipaa": [r"\bHIPAA\b"],
        "full_backend_replacement": [
            r"\b(?:replace|eliminate|remove|retire)s?\b.{0,30}\bback[ -]?end\b"
        ],
    }
    if normalized in known:
        return known[normalized]
    words = [word for word in re.findall(r"[a-z0-9]+", normalized) if len(word) > 2]
    if not words:
        return []
    return [r"\b" + r"\W+".join(re.escape(word) for word in words) + r"\b"]


def write_artifacts(report: CampaignQualityReport, out: Path) -> tuple[Path, Path]:
    out.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(report.campaign_id)
    json_path = out / f"{stem}.json"
    markdown_path = out / f"{stem}.md"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def render_markdown(report: CampaignQualityReport) -> str:
    finding_count = sum(len(draft.findings) for draft in report.drafts)
    safety_count = sum(
        1 for draft in report.drafts for finding in draft.findings if str(finding.kind) == "safety"
    )
    lines = [
        f"# Campaign quality: {report.campaign_name or report.campaign_id}",
        "",
        f"- Verdict: **{report.verdict}**",
        f"- Evidentially safe: **{'yes' if report.evidentially_safe else 'no'}**",
        f"- Commercial review: **{report.commercial_review_status}**",
        f"- Mode: **{'live + deterministic' if report.live else 'deterministic only'}**",
        f"- Drafts: {len(report.drafts)}",
        f"- Findings: {finding_count} ({safety_count} safety)",
        f"- Source: {_md(report.source)}",
        "",
    ]
    if not report.live:
        lines.extend(
            [
                "> Commercial model review was not run. Deterministic execution spends no model quota.",
                "",
            ]
        )

    for draft in report.drafts:
        lines.extend(
            [
                f"## Draft {_md(draft.draft_id)} (email {draft.position})",
                "",
                "| Rule | Check | Result |",
                "| --- | --- | --- |",
                *[
                    f"| {check.rule_id} | {_md(check.name)} | "
                    f"{'PASS' if check.passed else f'FAIL ({len(check.findings)})'} |"
                    for check in draft.checks
                ],
                "",
            ]
        )
        if draft.findings:
            lines.extend(
                [
                    "### Findings",
                    "",
                    "| Severity | Rule | Location | Offending text | Detail | References |",
                    "| --- | --- | --- | --- | --- | --- |",
                ]
            )
            for finding in draft.findings:
                lines.append(
                    f"| {finding.severity} | {finding.rule_id} | {_md(finding.location)} | "
                    f"{_md(finding.offending_text)} | {_md(finding.message)} | "
                    f"{_md(', '.join(finding.reference_ids) or '—')} |"
                )
            lines.append("")

    if report.commercial_review is not None:
        lines.extend(
            [
                "## Live commercial review",
                "",
                "Draft identities were hidden from the model. Anonymous order rotates by persona.",
                f"Model calls: {report.commercial_review.model_calls}.",
                "",
            ]
        )
        for persona in report.commercial_review.personas:
            lines.extend([f"### {_md(persona.persona)}", ""])
            if not persona.reported:
                lines.extend([f"Review unavailable: {_md(persona.error)}", ""])
                continue
            lines.extend(
                [
                    "| Draft | Average | Specificity | Problem | Trust | Value | Difference | Readability | CTA | Interest | Natural tone |",
                    "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
                ]
            )
            for draft in persona.drafts:
                rubric = draft.rubric
                lines.append(
                    f"| {draft.blind_label} → {_md(draft.draft_id)} | {rubric.average_score:.2f} | "
                    f"{rubric.specificity_to_audience_company.score} | "
                    f"{rubric.relevance_of_problem.score} | {rubric.credibility_trust.score} | "
                    f"{rubric.value_clarity.score} | {rubric.differentiation.score} | "
                    f"{rubric.readability_flow.score} | {rubric.cta_quality.score} | "
                    f"{rubric.likely_reply_interest.score} | "
                    f"{rubric.spamminess_generic_ai_tone.score} |"
                )
            winner = (
                f"{persona.winner_blind_label} → {persona.winner_draft_id}"
                if persona.winner_draft_id
                else persona.winner_blind_label or "not reported"
            )
            lines.extend(
                [
                    "",
                    f"Winner: **{_md(winner)}** — {_md(persona.comparison_evidence)}",
                    "",
                ]
            )

    lines.extend(["## Revision priorities", ""])
    if report.revision_priorities:
        lines.extend(
            f"{index}. {_md(priority)}"
            for index, priority in enumerate(report.revision_priorities, 1)
        )
    else:
        lines.append("No deterministic or live-review revisions were identified.")
    if report.notes:
        lines.extend(["", "## Notes", "", *[f"- {_md(note)}" for note in report.notes]])
    lines.append("")
    return "\n".join(lines)


def _safe_stem(value: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-.")
    return stem or "campaign-quality"


def _md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _session(model: str | None, execution_id: str) -> ModelSession:
    overrides = {CommercialReviewer.ROLE_ID: model} if model else None
    return ModelSession(
        provider=get_ai_provider(),
        prompt_engine=get_prompt_engine(PROMPTS_DIR),
        events=EventBus(),
        model_router=ModelRouter(overrides),
        execution_id=execution_id,
    )


async def _run(args: argparse.Namespace) -> list[tuple[CampaignQualityReport, Path, Path]]:
    cases = [load_case(reference) for reference in args.campaign]
    if args.live:
        calls = sum(max(1, len(case.context.buyer_personas)) for case in cases)
        print(
            f"Live commercial review enabled: about {calls} model call(s). "
            "This spends configured model quota.",
            flush=True,
        )

    written: list[tuple[CampaignQualityReport, Path, Path]] = []
    for case in cases:
        reviewer = (
            CommercialReviewer(_session(args.model, f"campaign-quality-{case.id}"))
            if args.live
            else None
        )
        report = await evaluate_campaign(case, reviewer)
        json_path, markdown_path = write_artifacts(report, args.out)
        written.append((report, json_path, markdown_path))
        print(
            f"{case.id}: {report.verdict} — {json_path} — {markdown_path}",
            flush=True,
        )
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--campaign",
        action="append",
        required=True,
        help="campaign UUID, fixture name, or fixture JSON path (repeatable)",
    )
    parser.add_argument("--out", required=True, type=Path, help="artifact output directory")
    parser.add_argument(
        "--live",
        action="store_true",
        help="opt in to blind model-based commercial review; spends model quota",
    )
    parser.add_argument(
        "--model",
        help="optional configured model slug for the live reviewer (default: balanced tier)",
    )
    args = parser.parse_args(argv)
    if args.model and not args.live:
        parser.error("--model only applies with --live")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        asyncio.run(_run(args))
    except CampaignQualityLoadError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
