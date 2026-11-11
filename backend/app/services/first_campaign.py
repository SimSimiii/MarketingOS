"""Prepare one source-backed acquisition draft with a bounded preparation pass."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from time import monotonic
from uuid import UUID

from sqlalchemy import Engine
from sqlmodel import Session

from app.ai.base import AIProvider
from app.auth.principal import Principal
from app.knowledge.store import ArtifactScope, ArtifactStore, fingerprint_documents
from app.market.audience_research import research_from_map
from app.market.relevance import CampaignReadiness, recommendation_for_request
from app.models.brand import Brand
from app.models.user import User
from app.runtime.model_session import RoleCall
from app.schemas.campaign import CampaignCreateRequest
from app.services.campaign_service import CampaignService
from app.services.knowledge_compilation import CompilationJob, _compile
from app.services.knowledge_service import KnowledgeService
from app.services.market_service import (
    JobStatus,
    MarketError,
    MarketService,
    _require_search,
    _run_audience_map,
    _run_audience_research,
    _run_relevance_dossier,
    _run_scan,
)

logger = logging.getLogger(__name__)
# Cold compilation plus source-backed audience research exceeded eight minutes
# in the homepage audit. Keep a finite pass without forcing a second launch
# before the saved recommendation can be assessed.
_PREPARATION_SECONDS = 900


class _StageProgress(JobStatus):
    def __init__(self, parent: JobStatus) -> None:
        super().__init__(kind=parent.kind, brand_id=parent.brand_id)
        self._parent = parent

    def say(self, message: str) -> None:
        super().say(message)
        self._parent.say(message)

    def record(self, call: RoleCall) -> None:
        self._parent.record(call)


async def prepare_first_campaign(
    brand_id: UUID, provider: AIProvider, engine: Engine, status: JobStatus, objective: str,
) -> None:
    deadline = monotonic() + _PREPARATION_SECONDS
    request = f"Write exactly one email. {objective}"

    def check_time() -> None:
        if monotonic() >= deadline:
            raise MarketError(
                "Preparation reached its time budget. Saved research can be reused when you continue."
            )

    async def stage(label: str, run: Callable[[JobStatus], Awaitable[None]]) -> None:
        check_time()
        status.say(label)
        child = _StageProgress(status)
        await run(child)
        if child.state != "done":
            raise MarketError(child.error or child.message or label)

    def finish(message: str) -> None:
        status.summary = message
        status.say(message)
        status.state = "done"

    try:
        with Session(engine) as db:
            brand = db.get(Brand, brand_id)
            if brand is None:
                raise MarketError("This brand no longer exists.")
            scope = ArtifactScope(brand_id=brand_id)
            artifacts = ArtifactStore(db)
            documents = artifacts.source_documents(scope)
            if not documents:
                if not brand.website_url:
                    raise MarketError("Add the brand website or a source document.")
                status.say("Reading the brand website and its most useful linked pages")
                await KnowledgeService(db).ingest_source(brand.website_url, brand_id=brand_id, max_pages=9)
                documents = artifacts.source_documents(scope)
            if await KnowledgeService(db).refresh_imported_logo(brand):
                status.say("The imported logo is unavailable; the email will use the brand name")
            stored = artifacts.load(scope)
            recompiled = stored is None or stored.fingerprint != fingerprint_documents(documents)
            if recompiled:
                check_time()
                status.say("Compiling the product facts needed for the first campaign")
                job = CompilationJob(state="running", brand_id=brand_id, brand_name=brand.name)
                await _compile(brand_id, engine, provider, job, compact=True,
                               on_progress=status.say, on_call=status.record)
                if job.state != "completed":
                    raise MarketError(job.message)
            else:
                status.say("Reusing the compiled knowledge")

            market = MarketService(db)
            stages: list[tuple[str, Callable[[JobStatus], Awaitable[None]]]] = []
            if market.snapshot(brand_id) is None:
                _require_search(provider, "rival_scout")
                stages.append(("Checking the main market alternative", lambda job: _run_scan(
                    brand_id, provider, engine, True, job, compact=True,
                )))
            demand = market.demand(brand_id)
            if demand is None or recompiled:
                _require_search(provider, "audience_cartographer")
                stages.append(("Comparing the strongest audience hypotheses", lambda job: _run_audience_map(
                    brand_id, provider, engine, job, compact=True,
                )))
            if stages:
                outcomes = await asyncio.gather(
                    *(stage(label, run) for label, run in stages), return_exceptions=True,
                )
                for outcome in outcomes:
                    if isinstance(outcome, BaseException):
                        raise outcome
                demand = market.demand(brand_id)
            if demand is None:
                raise MarketError("No audience map was saved.")
            candidates = [
                item for item in demand.ranked
                if item.assessment.compatibility != "incompatible"
                and (demand.admission_for(item, allow_topic_research=True).researchable
                     or research_from_map(item, demand.source_cache) is not None)
            ]

            def current_fit_first(item) -> int:
                receipt = market.relevance_status(brand_id, item.name)
                ready = (receipt.status == "current" and receipt.dossier is not None
                         and receipt.dossier.recommendation is not None
                         and recommendation_for_request(receipt.dossier, request).readiness in {
                             CampaignReadiness.GO, CampaignReadiness.GO_NARROW,
                         })
                return 0 if ready else 1

            # A ready, source-backed recommendation beats repurchasing research
            # for a higher-ranked but still unverified audience hypothesis.
            candidates = sorted(candidates, key=current_fit_first)[:2]
            if not candidates:
                first = demand.ranked[0] if demand.ranked else None
                why = demand.admission_for(first).reasons[:1] if first else []
                finish(
                    " ".join(["No audience has a concrete, researchable need yet.", *why])
                )
                return
            recovery_attempted = False
            for candidate in candidates:
                check_time()
                status.audience = candidate.name
                research = market.store.latest_research(brand_id, candidate.name)
                if research is None:
                    _require_search(provider, "audience_researcher")
                    await stage("Checking evidence for the audience", lambda job, segment=candidate.name: _run_audience_research(
                        brand_id, provider, engine, job, segment=segment, compact=True,
                    ))
                receipt = market.relevance_status(brand_id, candidate.name)
                automatic_request = request if getattr(candidate, "added_by", "") == "cartographer" else ""
                saved_scope = getattr(receipt.dossier, "first_email_scope", None) if receipt.dossier else None
                needs_scope = (automatic_request and receipt.dossier is not None
                               and (saved_scope is None or saved_scope.request != request
                                    or saved_scope.audience_decision_question is None))
                if receipt.status != "current" or needs_scope:
                    await stage("Matching the audience's need to verified product facts", lambda job, segment=candidate.name, draft=automatic_request: _run_relevance_dossier(
                        brand_id, provider, engine, job, segment=segment, compact=True,
                        draft_request=draft,
                    ))
                    receipt = market.relevance_status(brand_id, candidate.name)
                if receipt.status != "current" or receipt.dossier is None:
                    raise MarketError("No current recommendation was saved. Review the audience dossier.")
                gaps = receipt.dossier.product_gaps_to_verify()
                recommendation = recommendation_for_request(receipt.dossier, request)
                saved_scope = getattr(receipt.dossier, "first_email_scope", None)
                decision_question = (saved_scope.audience_decision_question
                                     if saved_scope and saved_scope.request == request else "")
                can_draft = recommendation is not None and recommendation.readiness in {
                    CampaignReadiness.GO, CampaignReadiness.GO_NARROW,
                }
                if decision_question and not can_draft:
                    gaps = [decision_question]
                # Optional decision questions must not buy another research
                # pass when the saved contract already permits a scoped draft.
                if gaps and not can_draft and not receipt.dossier.verified_product_questions and not recovery_attempted:
                    recovery_attempted = True
                    _require_search(provider, "material_researcher")
                    await stage("Checking the product questions that can change the recommendation",
                                lambda job, segment=candidate.name, questions=gaps,
                                knowledge_id=receipt.dossier.knowledge_id, draft=automatic_request: _run_relevance_dossier(
                                    brand_id, provider, engine, job, segment=segment,
                                    product_gaps=questions, expected_knowledge_id=knowledge_id, compact=True,
                                    draft_request=draft,
                                ))
                    receipt = market.relevance_status(brand_id, candidate.name)
                recommendation = recommendation_for_request(receipt.dossier, request) if receipt.dossier else None
                if receipt.status != "current" or recommendation is None:
                    finish("New evidence is saved. Recheck product fit in the audience map before drafting.")
                    return
                if recommendation.readiness in {CampaignReadiness.GO, CampaignReadiness.GO_NARROW}:
                    break
                next_action = recommendation.recommended_next_action or "Review the evidence for this audience before drafting."
                current_scope = getattr(receipt.dossier, "first_email_scope", None)
                current_question = (current_scope.audience_decision_question
                                    if current_scope and current_scope.request == request else "")
                remaining = ([current_question] if current_question else
                             receipt.dossier.product_gaps_to_verify() or recommendation.unresolved_objections)
                explanation = " ".join([next_action, *remaining[:1]])
                status.say(f"Audience needs further verification: {candidate.name}. {explanation}")
            else:
                finish("No email is ready for this objective. Your sources and research are saved. "
                       "Describe a narrower supported use below or review the audience evidence. "
                       + explanation)
                return

            owner = db.get(User, brand.owner_id) if brand.owner_id else None
            if brand.owner_id and owner is None:
                raise MarketError("The brand owner is no longer available.")
            principal = Principal(owner)
            campaign = CampaignService(db, provider, principal).create_campaign(CampaignCreateRequest(
                name=f"{brand.name[:226]} — first campaign",
                request=request,
                brand_id=brand_id,
                audience_segment=candidate.name,
                policy_preset="fast",
                strategy_mode="planned",
            ))
            status.campaign_id = campaign.id
            finish(" ".join(filter(None, [
                receipt.dossier.orientation,
                next(iter(recommendation.reasons), ""),
                recommendation.recommended_next_action,
            ])) or "Review the suggested audience and generate your email.")
    except asyncio.CancelledError:
        status.error = "Preparation was interrupted. Saved results can be reused."
        status.state = "failed"
        status.say(status.error)
        raise
    except (MarketError, ValueError) as exc:
        status.error = str(exc)
        status.state = "failed"
        status.say(status.error)
    except Exception:
        logger.exception("First campaign preparation failed for %s", brand_id)
        status.error = "Preparation stopped. Saved research can be reused when you continue."
        status.state = "failed"
        status.say(status.error)
    finally:
        status.finished_at = datetime.now(UTC)
