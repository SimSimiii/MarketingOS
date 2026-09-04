import statistics
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete
from sqlmodel import Session, col

from app.ai.base import AIProvider
from app.ai.roles import validate_overrides
from app.knowledge.store import ArtifactScope, ArtifactStore, fingerprint_documents
from app.marketing.contract import parse_contract
from app.marketing.forecast import forecast
from app.marketing.policy import resolve_policy
from app.models.agent_execution import AgentExecution
from app.models.campaign import Campaign
from app.models.campaign_execution import CampaignExecution
from app.models.enums import CampaignStatus, ExecutionStatus, LogLevel
from app.models.execution_log import ExecutionLog
from app.models.generated_asset import GeneratedAsset
from app.models.knowledge_artifacts import KnowledgeArtifactSet
from app.models.knowledge_document import KnowledgeDocument
from app.models.market import ProspectRow
from app.orchestration import execution_manager
from app.orchestration.execution_registry import registry
from app.repositories.agent_execution_repository import AgentExecutionRepository
from app.repositories.campaign_execution_repository import CampaignExecutionRepository
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.execution_log_repository import ExecutionLogRepository
from app.repositories.generated_asset_repository import GeneratedAssetRepository
from app.repositories.knowledge_repository import KnowledgeDocumentRepository
from app.schemas.campaign import (
    CampaignCreateRequest,
    CampaignGenerationAdvice,
    CampaignPolicyUpdate,
    RunForecast,
)

#: Rough conversion from the word count a document stores to the characters
#: the evidence pass reads. Only ever feeds a call-count estimate, and the
#: estimate is a range: an average English word plus its space is close
#: enough that a page either does or does not need a second reading.
_CHARS_PER_WORD = 6


#: The keys `update_policy` reconstructs itself. Everything else in the
#: policy dict is an ExecutionPolicy field override, carried forward as a
#: group when a request does not restate it.
_REBUILT_KEYS = frozenset({"preset", "email_tier"})


def _audience_key(value: str) -> str:
    return " ".join(value.casefold().split())


class CampaignAlreadyRunningError(Exception):
    """Raised when a campaign already has an execution in flight - starting
    a second one concurrently would let two pipelines write the same
    campaign's story at once."""


class NoExecutionToRestartError(Exception):
    """Raised when /restart is called on a campaign that has never run."""


class ExecutionNotCancellableError(Exception):
    """Raised when /cancel is called on an execution that isn't running."""


class CampaignTargetError(ValueError):
    """A company target does not belong to this brand/audience."""


class CampaignService:
    """Business logic for campaigns: CRUD, lifecycle, and kicking off / reading runs."""

    def __init__(self, session: Session, ai_provider: AIProvider) -> None:
        self._session = session
        #: The engine backing THIS request's session - not a hardcoded
        #: global - so a background run (see execution_manager.launch) opens
        #: its own session against the same database, real or test.
        self._engine = session.get_bind()
        self._campaigns = CampaignRepository(session)
        self._executions = CampaignExecutionRepository(session)
        self._agent_executions = AgentExecutionRepository(session)
        self._generated_assets = GeneratedAssetRepository(session)
        self._logs = ExecutionLogRepository(session)
        self._knowledge = KnowledgeDocumentRepository(session)
        self._ai_provider = ai_provider

    # --------------------------------------------------------------- CRUD

    def create_campaign(self, data: CampaignCreateRequest) -> Campaign:
        fields = data.model_dump(
            exclude={"policy_preset", "model_overrides", "force_recompile", "email_tier"}
        )
        policy: dict | None = None
        if data.policy_preset is not None:
            policy = {"preset": data.policy_preset}
        if data.force_recompile is not None:
            policy = {**(policy or {}), "force_recompile": data.force_recompile}
        if data.email_tier is not None:
            # Into the policy dict, which is where `_presentation` reads it
            # from. Stored as its value rather than the enum so the JSON column
            # round-trips to a plain string.
            policy = {**(policy or {}), "email_tier": str(data.email_tier)}
        if data.prospect_id is not None:
            prospect = self._session.get(ProspectRow, data.prospect_id)
            if prospect is None:
                raise CampaignTargetError("The selected company no longer exists.")
            if data.brand_id is None or prospect.brand_id != data.brand_id:
                raise CampaignTargetError("The selected company does not belong to this brand.")
            if data.audience_segment and _audience_key(prospect.segment) != _audience_key(
                data.audience_segment
            ):
                raise CampaignTargetError(
                    "The selected company was qualified for a different audience segment."
                )
            fields["audience_segment"] = prospect.segment
        return self._campaigns.create(
            Campaign(
                **fields,
                policy=policy,
                # Checked before the row exists. An override that names an
                # agent nothing answers to, or a model that cannot do what the
                # agent needs, is a mistake worth catching at the dialog rather
                # than thirteen minutes into the run it breaks.
                model_overrides=validate_overrides(data.model_overrides) or None,
            )
        )

    def get_campaign(self, campaign_id: UUID) -> Campaign | None:
        return self._campaigns.get(campaign_id)

    def list_campaigns(self, include_archived: bool = False) -> list[Campaign]:
        return self._campaigns.list_all() if include_archived else self._campaigns.list_active()

    def latest_run_by_campaign(self) -> dict[UUID, tuple[ExecutionStatus, datetime]]:
        """Feeds CampaignRead.last_run_status for a whole list in one query."""
        return self._executions.latest_by_campaign()  # type: ignore[return-value]

    def delete_campaign(self, campaign: Campaign) -> None:
        """Remove the campaign and everything that belongs to it.

        Done as a handful of bulk statements in ONE transaction rather than
        row-by-row: a campaign with a few runs owns hundreds of log, asset and
        agent-execution rows, and the per-row repository helpers commit on
        every single one. Children go first - assets and logs reference the
        agent executions and campaign executions above them.
        """
        if registry.is_campaign_running(campaign.id):
            raise CampaignAlreadyRunningError(
                "Cannot delete a campaign with a run in progress - cancel it first."
            )

        execution_ids = [
            execution.id for execution in self._executions.list_by_campaign(campaign.id)
        ]
        if execution_ids:
            for model in (GeneratedAsset, ExecutionLog, AgentExecution):
                self._session.execute(
                    delete(model).where(col(model.campaign_execution_id).in_(execution_ids))
                )
            self._session.execute(
                delete(CampaignExecution).where(col(CampaignExecution.id).in_(execution_ids))
            )
        self._session.execute(
            delete(KnowledgeDocument).where(col(KnowledgeDocument.campaign_id) == campaign.id)
        )
        # Knowledge compiled for this campaign alone dies with it; a brand's
        # artifacts outlive any one campaign and are never touched here.
        self._session.execute(
            delete(KnowledgeArtifactSet).where(
                col(KnowledgeArtifactSet.campaign_id) == campaign.id
            )
        )
        self._session.delete(campaign)
        self._session.commit()

    def archive_campaign(self, campaign: Campaign) -> Campaign:
        campaign.status = CampaignStatus.ARCHIVED
        campaign.archived_at = datetime.now(UTC)
        campaign.updated_at = datetime.now(UTC)
        return self._campaigns.update(campaign)

    def unarchive_campaign(self, campaign: Campaign) -> Campaign:
        campaign.status = CampaignStatus.ACTIVE
        campaign.archived_at = None
        campaign.updated_at = datetime.now(UTC)
        return self._campaigns.update(campaign)

    def duplicate_campaign(self, campaign: Campaign) -> Campaign:
        """Copies the brief and attached knowledge - never past executions,
        which belong to the run that produced them, not to the campaign."""
        clone = self._campaigns.create(
            Campaign(
                name=f"{campaign.name} (copy)",
                brand_id=campaign.brand_id,
                request=campaign.request,
                product_description=campaign.product_description,
                product_url=campaign.product_url,
                target_market=campaign.target_market,
                goals=campaign.goals,
                audience_segment=campaign.audience_segment,
                prospect_id=campaign.prospect_id,
                sender_name=campaign.sender_name,
                sender_role=campaign.sender_role,
                cta_url=campaign.cta_url,
                policy=campaign.policy,
                model_overrides=campaign.model_overrides,
            )
        )
        for document in self._knowledge.list_by_campaign(campaign.id):
            self._knowledge.create(
                KnowledgeDocument(
                    campaign_id=clone.id,
                    brand_id=document.brand_id,
                    title=document.title,
                    source_type=document.source_type,
                    content=document.content,
                    source_url=document.source_url,
                    word_count=document.word_count,
                    document_metadata=document.document_metadata,
                )
            )
        return clone

    def update_policy(self, campaign: Campaign, data: CampaignPolicyUpdate) -> Campaign:
        # Validated eagerly so a bad preset/override never reaches a running
        # campaign - the router only sees good data.
        resolve_policy(data.preset, data.overrides)
        # `policy` is rebuilt rather than merged, so every key stored in it that
        # this request does not carry has to be put back by hand - in all three
        # directions, not one. The preset, the field overrides and the tier are
        # each set from a different screen, so whichever is absent from a
        # request is exactly the one that would otherwise be silently reset.
        #
        # Only the tier direction was wired, because at the time no request
        # arrived without a preset. One does: saving a model pin carries neither
        # preset nor tier, and quietly moved a `maximum` campaign back to
        # `balanced` - a different number of drafts, different judges and a
        # different budget than the user chose.
        #
        # `None` leaves what is stored alone and `{}` clears it, matching
        # model_overrides below.
        stored = campaign.policy or {}
        preset = data.preset if data.preset is not None else stored.get("preset")
        overrides = (
            data.overrides
            if data.overrides is not None
            else {key: value for key, value in stored.items() if key not in _REBUILT_KEYS}
        )
        tier = data.email_tier if data.email_tier is not None else stored.get("email_tier")

        policy: dict = {"preset": preset} if preset else {}
        policy.update(overrides)
        if tier is not None:
            policy["email_tier"] = str(tier)
        campaign.policy = policy or None
        if data.model_overrides is not None:
            # `None` leaves the stored pins alone; `{}` is how the picker says
            # "back to the preset's models". The two have to stay distinct, or
            # changing the preset from a screen that does not show the picker
            # would clear it.
            campaign.model_overrides = validate_overrides(data.model_overrides) or None
        campaign.updated_at = datetime.now(UTC)
        return self._campaigns.update(campaign)

    # ----------------------------------------------------------- forecast

    def forecast_run(self, campaign: Campaign) -> RunForecast:
        """What running this campaign will cost, before it is bought.

        Two grounded numbers and no invented ones. The call count is
        arithmetic - nothing in the pipeline spends a model call deciding what
        happens next, so the shape of a run is fixed by the policy and by the
        number of emails parsed out of the request. The money is the user's
        own history: what past runs on this preset actually cost, which is a
        measurement rather than a price list, and which gets better the more
        they run.

        Deliberately no cost-per-call conversion between the two. That would
        be a made-up constant sitting between two real numbers, and it is
        exactly the sort of figure that gets quoted back as though somebody
        had measured it.
        """
        policy = resolve_policy(
            (campaign.policy or {}).get("preset"),
            {k: v for k, v in (campaign.policy or {}).items() if k != "preset"} or None,
        )
        contract = parse_contract(campaign.request)

        store = ArtifactStore(self._session)
        scope = ArtifactScope.for_campaign(campaign)
        documents = store.source_documents(scope)
        stored = store.load(scope)
        reused = (
            stored is not None
            and stored.fingerprint == fingerprint_documents(documents)
            and not policy.force_recompile
        )
        estimate = forecast(
            policy,
            contract,
            material_chars=sum(document.word_count * _CHARS_PER_WORD for document in documents),
            knowledge_reused=reused,
        )
        # Read once. Both figures below describe the same set of past runs,
        # and finding it walks every campaign the user has ever made.
        runs = self._comparable_runs(campaign)
        return RunForecast(
            preset=(campaign.policy or {}).get("preset") or "balanced",
            emails=contract.count,
            count_is_explicit=contract.count_is_explicit,
            low=estimate.low,
            high=estimate.high,
            compile_low=estimate.compile_low,
            compile_high=estimate.compile_high,
            knowledge_reused=reused,
            observed_runs=len(runs),
            observed_cost_per_email=_observed_cost(runs),
        )

    def _comparable_runs(self, campaign: Campaign) -> list[tuple[float, int]]:
        """(cost, emails delivered) for finished runs configured like this one.

        Same preset, because the preset is what decides how many calls a run
        makes. Across campaigns, because a new campaign has no history of its
        own and the user's other runs are the best evidence there is.

        Only runs that **finished and delivered**. A run that died on its
        first call cost a penny, and quoting that as the bottom of the range
        would say a campaign might cost a penny - it says nothing except that
        something went wrong.
        """
        preset = (campaign.policy or {}).get("preset") or "balanced"
        wanted = {
            other.id
            for other in self._campaigns.list_all()
            if ((other.policy or {}).get("preset") or "balanced") == preset
        }
        runs: list[tuple[float, int]] = []
        for execution in self._executions.list_by_campaigns(wanted):
            delivered = ((execution.result or {}).get("report") or {}).get("delivered") or 0
            if (
                execution.status is ExecutionStatus.COMPLETED
                and execution.estimated_cost_usd > 0
                and delivered > 0
            ):
                runs.append((execution.estimated_cost_usd, int(delivered)))
        return runs

    # ---------------------------------------------------------- execution

    def generation_advice(self, campaign: Campaign) -> CampaignGenerationAdvice:
        """Free deterministic preflight; it never launches or calls a model."""
        from app.market.qualification import QualificationClass
        from app.market.relevance import (
            CampaignReadiness,
            CampaignRecommendation,
            DossierState,
            RecommendationState,
        )
        from app.services.market_service import MarketService

        selected = (campaign.audience_segment or "").strip()
        if campaign.brand_id is None or not selected:
            return CampaignGenerationAdvice(
                campaign_id=campaign.id,
                readiness=CampaignReadiness.GO,
                reasons=["No persisted market recommendation applies to this campaign."],
                user_message="No audience-level qualification recommendation applies.",
            )

        market = MarketService(self._session)
        status = market.relevance_status(campaign.brand_id, selected)
        recommendation = status.dossier.recommendation if status.dossier else None
        if recommendation is None:
            recommendation = CampaignRecommendation(
                state=RecommendationState.DISCOVERY_ONLY,
                readiness=CampaignReadiness.DISCOVERY_ONLY,
                reasons=[
                    "No current V2 recommendation establishes product-to-audience fit."
                ],
                recommended_next_action=(
                    "Build or rebuild the Relevance Dossier V2, or generate explicitly as "
                    "an audience-level hypothesis."
                ),
                override_risk=(
                    "The campaign may be weak because product fit has not been qualified. "
                    "Copy remains limited to licensed product claims."
                ),
            )
        elif status.status is not DossierState.CURRENT:
            recommendation = recommendation.model_copy(
                update={
                    "state": RecommendationState.DISCOVERY_ONLY,
                    "readiness": CampaignReadiness.DISCOVERY_ONLY,
                    "reasons": [
                        *recommendation.reasons,
                        "The V2 recommendation is stale against its current inputs.",
                    ],
                    "recommended_next_action": (
                        "Rebuild the relevance dossier before treating this audience or "
                        "its companies as qualified."
                    ),
                    "override_risk": (
                        "The product profile, research, market scan, or company "
                        "qualifications changed after this recommendation was built."
                    ),
                }
            )

        reasons = list(recommendation.reasons)
        selected_name = ""
        selected_qualification = None
        company_requires_override = False
        if campaign.prospect_id is not None:
            row = self._session.get(ProspectRow, campaign.prospect_id)
            if row is None or row.brand_id != campaign.brand_id:
                reasons.append("The selected company is no longer available for qualification.")
                company_requires_override = True
            else:
                selected_name = row.name
                selected_qualification = market.current_company_qualification(
                    campaign.brand_id, selected, row
                )
                if selected_qualification.classification is not QualificationClass.QUALIFIED:
                    reasons.append(
                        f"{row.name} is {selected_qualification.classification}, not QUALIFIED."
                    )
                    company_requires_override = True

        negative = recommendation.readiness in {
            CampaignReadiness.DISCOVERY_ONLY,
            CampaignReadiness.NO_GO,
        }
        narrow_outside = (
            recommendation.readiness is CampaignReadiness.GO_NARROW
            and campaign.prospect_id is not None
            and company_requires_override
        )
        override_required = negative or narrow_outside or company_requires_override
        message = (
            recommendation.override_risk
            if override_required
            else recommendation.recommended_next_action
        )
        return CampaignGenerationAdvice(
            campaign_id=campaign.id,
            readiness=recommendation.readiness,
            recommendation=recommendation,
            dossier_status=str(status.status),
            selected_company_name=selected_name,
            selected_company_qualification=selected_qualification,
            reasons=list(dict.fromkeys(reasons)),
            override_required=override_required,
            user_message=message,
        )

    async def start_execution(
        self, campaign: Campaign, *, generate_anyway: bool = False
    ) -> CampaignExecution:
        if registry.is_campaign_running(campaign.id):
            raise CampaignAlreadyRunningError(
                "This campaign already has a run in progress."
            )
        advice = self.generation_advice(campaign)
        snapshot = advice.model_dump(mode="json")
        # The recommendation is advisory, not an API permission system. The
        # UI uses ``generate_anyway`` to record that the warning was the
        # deliberate action the operator clicked; API clients remain free to
        # launch without a confirmation handshake, and the receipt still says
        # the run happened despite a negative/narrow recommendation.
        snapshot["override_explicit"] = generate_anyway
        return execution_manager.launch(
            campaign,
            self._ai_provider,
            self._engine,
            recommendation_snapshot=snapshot,
            generated_despite_recommendation=advice.override_required,
        )

    async def restart_execution(
        self, campaign: Campaign, *, generate_anyway: bool = False
    ) -> CampaignExecution:
        executions = self._executions.list_by_campaign(campaign.id)
        if not executions:
            raise NoExecutionToRestartError("This campaign has never been run.")
        return await self.start_execution(campaign, generate_anyway=generate_anyway)

    def cancel_execution(self, execution: CampaignExecution) -> None:
        if not registry.cancel(execution.id):
            raise ExecutionNotCancellableError("This execution isn't currently running.")

    def list_executions(self, campaign_id: UUID) -> list[CampaignExecution]:
        return self._executions.list_by_campaign(campaign_id)

    def get_execution(self, execution_id: UUID) -> CampaignExecution | None:
        return self._executions.get(execution_id)

    def get_agent_executions(self, execution_id: UUID) -> list[AgentExecution]:
        return self._agent_executions.list_by_execution(execution_id)

    def get_generated_assets(self, execution_id: UUID) -> list[GeneratedAsset]:
        return self._generated_assets.list_by_execution(execution_id)

    def is_execution_running(self, execution_id: UUID) -> bool:
        return registry.get(execution_id) is not None

    # ------------------------------------------------------------- live view

    def get_execution_logs(
        self,
        execution_id: UUID,
        agent_id: str | None = None,
        levels: list[LogLevel] | None = None,
        after_sequence: int | None = None,
        limit: int | None = None,
    ) -> list[ExecutionLog]:
        return self._logs.list_by_execution(
            execution_id,
            agent_id=agent_id,
            levels=levels,
            after_sequence=after_sequence,
            limit=limit,
        )

    def get_execution_timeline(self, execution_id: UUID) -> tuple[list[dict], int]:
        """Replay of everything broadcast for this run, plus the position to
        resume the live stream from.

        Rows written before events carried payloads (or by an older schema)
        are rebuilt from their message, so an old run still renders as a
        timeline instead of an empty page.
        """
        rows = self._logs.list_by_execution(execution_id)
        events = [row.data or _payload_from_row(row) for row in rows]
        last_sequence = max((row.sequence for row in rows), default=0)
        return events, last_sequence

    def list_running_executions(self) -> list[tuple[CampaignExecution, Campaign | None]]:
        """In-flight runs paired with the campaign they belong to, so the
        dashboard can name them without a request per row."""
        executions = self._executions.list_running()
        campaigns = {
            campaign.id: campaign
            for campaign in self._campaigns.list_all()
            if campaign.id in {execution.campaign_id for execution in executions}
        }
        return [(execution, campaigns.get(execution.campaign_id)) for execution in executions]


def _observed_cost(runs: list[tuple[float, int]]) -> float:
    """What a delivered email has typically cost, over `_comparable_runs`. The
    middle run, not the average one and not the range.

    Per email rather than per run, because past runs were different lengths
    and a figure across them would be mostly noise about how long each one
    was. The median for the same reason `PanelRead.pull` uses one: a single
    run that died two calls in, or one that hit every rewrite it was allowed,
    should not be the number a user plans around. Multiplying it by the emails
    this campaign asks for is left to them - doing that arithmetic here would
    join two real measurements with an assumption and present the result as
    though it had been measured.

    Takes the runs rather than the campaign because the caller already has
    them: computing the set twice per forecast is what this argument replaced.
    """
    each = sorted(cost / delivered for cost, delivered in runs)
    return statistics.median(each) if each else 0.0


def _payload_from_row(row: ExecutionLog) -> dict:
    return {
        "type": row.event_type or "log",
        "execution_id": str(row.campaign_execution_id),
        "agent_id": row.agent_id,
        "step": row.step,
        "level": row.level.value,
        "message": row.message,
        "at": row.created_at.isoformat(),
    }
