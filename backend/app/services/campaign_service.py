import statistics
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete
from sqlmodel import Session, col

from app.ai.base import AIProvider
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
from app.orchestration import execution_manager
from app.orchestration.execution_registry import registry
from app.repositories.agent_execution_repository import AgentExecutionRepository
from app.repositories.campaign_execution_repository import CampaignExecutionRepository
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.execution_log_repository import ExecutionLogRepository
from app.repositories.generated_asset_repository import GeneratedAssetRepository
from app.repositories.knowledge_repository import KnowledgeDocumentRepository
from app.schemas.campaign import CampaignCreateRequest, CampaignPolicyUpdate, RunForecast

#: Rough conversion from the word count a document stores to the characters
#: the evidence pass reads. Only ever feeds a call-count estimate, and the
#: estimate is a range: an average English word plus its space is close
#: enough that a page either does or does not need a second reading.
_CHARS_PER_WORD = 6


class CampaignAlreadyRunningError(Exception):
    """Raised when a campaign already has an execution in flight - starting
    a second one concurrently would let two pipelines write the same
    campaign's story at once."""


class NoExecutionToRestartError(Exception):
    """Raised when /restart is called on a campaign that has never run."""


class ExecutionNotCancellableError(Exception):
    """Raised when /cancel is called on an execution that isn't running."""


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
            exclude={"policy_preset", "model_overrides", "force_recompile"}
        )
        policy: dict | None = None
        if data.policy_preset is not None:
            policy = {"preset": data.policy_preset}
        if data.force_recompile is not None:
            policy = {**(policy or {}), "force_recompile": data.force_recompile}
        return self._campaigns.create(
            Campaign(**fields, policy=policy, model_overrides=data.model_overrides)
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
        policy: dict = {"preset": data.preset} if data.preset else {}
        if data.overrides:
            policy.update(data.overrides)
        campaign.policy = policy or None
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
        typical = self._observed_cost(campaign)
        return RunForecast(
            preset=(campaign.policy or {}).get("preset") or "balanced",
            emails=contract.count,
            count_is_explicit=contract.count_is_explicit,
            low=estimate.low,
            high=estimate.high,
            compile_low=estimate.compile_low,
            compile_high=estimate.compile_high,
            knowledge_reused=reused,
            observed_runs=len(self._comparable_runs(campaign)),
            observed_cost_per_email=typical,
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
        for campaign_id in wanted:
            for execution in self._executions.list_by_campaign(campaign_id):
                delivered = ((execution.result or {}).get("report") or {}).get("delivered") or 0
                if (
                    execution.status is ExecutionStatus.COMPLETED
                    and execution.estimated_cost_usd > 0
                    and delivered > 0
                ):
                    runs.append((execution.estimated_cost_usd, int(delivered)))
        return runs

    def _observed_cost(self, campaign: Campaign) -> float:
        """What a delivered email has typically cost. The middle run, not the
        average one and not the range.

        Per email rather than per run, because past runs were different
        lengths and a figure across them would be mostly noise about how long
        each one was. The median for the same reason `PanelRead.pull` uses
        one: a single run that died two calls in, or one that hit every
        rewrite it was allowed, should not be the number a user plans around.
        Multiplying it by the emails this campaign asks for is left to them -
        doing that arithmetic here would join two real measurements with an
        assumption and present the result as though it had been measured.
        """
        each = sorted(cost / delivered for cost, delivered in self._comparable_runs(campaign))
        return statistics.median(each) if each else 0.0

    # ---------------------------------------------------------- execution

    async def start_execution(self, campaign: Campaign) -> CampaignExecution:
        if registry.is_campaign_running(campaign.id):
            raise CampaignAlreadyRunningError(
                "This campaign already has a run in progress."
            )
        return execution_manager.launch(campaign, self._ai_provider, self._engine)

    async def restart_execution(self, campaign: Campaign) -> CampaignExecution:
        executions = self._executions.list_by_campaign(campaign.id)
        if not executions:
            raise NoExecutionToRestartError("This campaign has never been run.")
        return await self.start_execution(campaign)

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
