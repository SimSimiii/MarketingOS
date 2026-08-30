import logging
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlmodel import Session

from app.ai.base import AIProvider
from app.ai.model_router import ModelRouter
from app.ai.roles import WILDCARD_ROLE
from app.core.config import PROMPTS_DIR
from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.corpus import SourceCorpus
from app.knowledge.store import ArtifactScope, ArtifactStore, StoredArtifacts, fingerprint_documents
from app.market.demand import DemandMap
from app.market.positioning import PositioningMap
from app.market.store import MarketStore, merge_audience, merge_proof
from app.marketing.briefs import CampaignBrief
from app.marketing.cancellation import CancellationToken
from app.marketing.craft import EmailVersion
from app.marketing.critic import Critique
from app.marketing.email_copy import Email, render_email
from app.marketing.gates import GateReport
from app.marketing.observer import RunObserver
from app.marketing.pipeline import (
    CampaignRunResult,
    EmailCampaignPipeline,
    KnowledgeGateway,
)
from app.marketing.policy import ExecutionPolicy, resolve_policy
from app.marketing.reader import PanelRead
from app.marketing.render_html import MAX_EMAIL_BYTES, BrandStyle, EmailTier, render_html
from app.marketing.report import CampaignReport
from app.marketing.request import CampaignRequest
from app.marketing.sequence import SequenceReport
from app.models.agent_execution import AgentExecution
from app.models.campaign import Campaign
from app.models.campaign_execution import CampaignExecution
from app.models.enums import AssetType, ExecutionStatus, LogLevel
from app.models.generated_asset import GeneratedAsset
from app.orchestration.event_emitter import ExecutionEventEmitter
from app.orchestration.live_broker import broker
from app.repositories.agent_execution_repository import AgentExecutionRepository
from app.repositories.brand_repository import BrandRepository
from app.repositories.campaign_execution_repository import CampaignExecutionRepository
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.execution_log_repository import ExecutionLogRepository
from app.repositories.generated_asset_repository import GeneratedAssetRepository
from app.runtime.events import (
    EventBus,
    ModelCallFinished,
    ModelCallRetried,
    ModelCallStarted,
)
from app.runtime.model_session import ModelSession, RoleCall
from app.runtime.prompt_engine import get_prompt_engine

logger = logging.getLogger("marketingos.orchestration")

#: Statuses that still handed the user usable emails. A run that timed out
#: after writing four of five did not fail - it delivered four, and saying
#: otherwise hides real work behind a red banner.
_DELIVERING_STATUSES = {
    "completed",
    "degraded",
    "timed_out",
    "budget_exhausted",
    "provider_unavailable",
}

#: Human names for the five reasoning roles, for the timeline. The old system
#: read these off an agent registry; there is no registry now because there is
#: nothing to look up at runtime - the roles are fixed.
ROLE_NAMES: dict[str, str] = {
    "knowledge_compiler": "Knowledge Compiler",
    "strategist": "Strategist",
    "email_writer": "Email Writer",
    "blind_reader": "Blind Reader",
    "conversion_critic": "Conversion Critic",
    "sequence_reviewer": "Sequence Reviewer",
    "preference_judge": "Side-by-Side Reader",
    "subject_writer": "Subject Lines",
    "inbox_scanner": "Inbox Glance",
}


def role_name(role_id: str) -> str:
    return ROLE_NAMES.get(role_id, role_id.replace("_", " ").title())


class _DbKnowledgeGateway(KnowledgeGateway):
    """The pipeline's window onto stored knowledge, backed by the database."""

    def __init__(self, session: Session, campaign: Campaign) -> None:
        self._store = ArtifactStore(session)
        self._session = session
        self._campaign = campaign
        self._scope = ArtifactScope.for_campaign(campaign)
        self._documents = self._store.source_documents(self._scope)
        self._corpus: SourceCorpus | None = None
        self._market = MarketStore(session) if campaign.brand_id is not None else None

    @property
    def scope(self) -> ArtifactScope:
        return self._scope

    def corpus(self) -> SourceCorpus:
        if self._corpus is None:
            self._corpus = self._store.corpus_for(self._scope)
        return self._corpus

    def fingerprint(self) -> str:
        return fingerprint_documents(self._documents)

    def load(self) -> StoredArtifacts | None:
        stored = self._store.load(self._scope)
        return self._with_market(stored)

    def save(self, artifacts: KnowledgeArtifacts, fingerprint: str) -> StoredArtifacts:
        return self._with_market(self._store.save(self._scope, artifacts, fingerprint))

    def positioning(self) -> PositioningMap | None:
        """The latest market scan for this brand, if there is one.

        Brand-scoped only. A one-off campaign with no brand has nowhere to
        keep a competitor list between runs, so scanning for it would buy a
        reading that is thrown away with the campaign.
        """
        if self._market is None or self._campaign.brand_id is None:
            return None
        snapshot = self._market.latest_scan(self._campaign.brand_id)
        return snapshot.positioning if snapshot is not None else None

    def demand(self) -> DemandMap | None:
        """The latest audience map for this brand, if there is one.

        Brand-scoped for the same reason the positioning is: a one-off
        campaign has nowhere to keep a map between runs.
        """
        if self._market is None or self._campaign.brand_id is None:
            return None
        return self._market.latest_map(self._campaign.brand_id)

    def audience_choice(self) -> str:
        return self._campaign.audience_segment or ""

    def _with_market(self, stored: StoredArtifacts | None) -> StoredArtifacts | None:
        """Fold in what the market pages decided, on top of what was compiled.

        Two merges, both at read time rather than written into the stored set,
        so a recompile cannot lose either - see `app.market.store`.

        The first is every third-party proof the user has approved: this is
        where a testimonial they ticked in the UI becomes a fact the writer
        may spend and the evidence gate will license.

        The second is the audience segment this campaign was pointed at, which
        goes to the head of the audience model. That single move is what makes
        the choice reach the copy: the strategist plans against it, the cold
        reader panel is built from it, and the critic grades against it, none
        of them knowing where it came from.

        Version and fingerprint are carried through untouched. They describe
        the *material* this was compiled from, and neither merge changed any
        material - treating them as changed would recompile the business every
        time somebody targeted a different buyer.
        """
        if stored is None or self._market is None or self._campaign.brand_id is None:
            return stored
        artifacts = stored.artifacts
        if approved := self._market.approved_evidence(self._campaign.brand_id):
            artifacts = merge_proof(artifacts, approved)
        if chosen := (self._campaign.audience_segment or ""):
            artifacts = merge_audience(
                artifacts, self._market.segment_named(self._campaign.brand_id, chosen)
            )
        if artifacts is stored.artifacts:
            return stored
        return StoredArtifacts(
            artifacts=artifacts,
            version=stored.version,
            fingerprint=stored.fingerprint,
        )

    def prior_learnings(self) -> str:
        """What the last finished campaign for this business found out.

        Only the most recent one: a Strategist reading five campaign reports
        spends its attention on history instead of on this campaign, and the
        newest report already carries forward the gaps that survived.
        """
        executions = CampaignExecutionRepository(self._session)
        campaigns = [self._campaign]
        if self._campaign.brand_id is not None:
            campaigns = CampaignRepository(self._session).list_by_brand(self._campaign.brand_id)

        for campaign in campaigns:
            for execution in executions.list_by_campaign(campaign.id):
                payload = (execution.result or {}).get("report")
                if not payload:
                    continue
                try:
                    return CampaignReport.model_validate(payload).render_learnings()
                except Exception:
                    logger.info("could not read a prior campaign report", exc_info=True)
        return ""


class _PersistenceObserver(RunObserver):
    """Watches the pipeline and persists what happened.

    The pipeline itself knows nothing about databases. Every hook goes through
    the execution's event emitter, so a watching client sees the same story the
    database will hold - that single funnel is the reason the live stream and
    a reloaded page can never disagree, and it survives the redesign untouched.

    A "step" here is one role invocation: one writer turn, one cold read, one
    critique. That is finer-grained than the old director's steps and more
    honest, because it is also the unit that costs money.
    """

    def __init__(
        self,
        orchestrator: "CampaignOrchestrator",
        execution: CampaignExecution,
        emitter: ExecutionEventEmitter,
    ) -> None:
        self._orchestrator = orchestrator
        self._execution = execution
        self._emitter = emitter
        self._step = 0
        self._open: dict[str, Any] | None = None
        self._calls: list[RoleCall] = []
        #: Which AgentExecution row last wrote each email, so the finished
        #: asset can be attached to the run that produced it.
        self.writer_rows: dict[int, UUID] = {}
        self.attempts: dict[str, int] = {}

    # ------------------------------------------------------------ recording

    def record_call(self, call: RoleCall) -> None:
        """Every model call lands in whichever step is currently open."""
        self._calls.append(call)

    def on_phase(self, phase: str, message: str, data: dict[str, Any] | None = None) -> None:
        self._emitter.emit(
            "phase",
            message,
            agent_id=self._open["role_id"] if self._open else None,
            data={"phase": phase, **(data or {})},
        )

    def on_role_started(
        self, role_id: str, label: str, data: dict[str, Any] | None = None
    ) -> None:
        if self._open is not None:
            # Defensive: a role that never reported finishing would otherwise
            # swallow the next one's tokens.
            self.on_role_finished(self._open["role_id"], "finished")
        self._step += 1
        self.attempts[role_id] = self.attempts.get(role_id, 0) + 1
        self._calls = []
        self._open = {
            "role_id": role_id,
            "label": label,
            "step": self._step,
            "started_at": datetime.now(UTC),
            "data": data or {},
        }
        self._emitter.current_step = self._step
        self._emitter.emit(
            "agent_started",
            f"{role_name(role_id)}: {label}",
            agent_id=role_id,
            step=self._step,
            data={"agent_name": role_name(role_id), "label": label, **(data or {})},
        )

    def on_role_finished(
        self, role_id: str, summary: str, output: dict[str, Any] | None = None
    ) -> None:
        open_step = self._close()
        if open_step is None:
            return
        row = self._persist_row(
            open_step, ExecutionStatus.COMPLETED, output_data=output, error=None
        )
        if role_id == "email_writer":
            position = open_step["data"].get("position")
            if position is not None:
                self.writer_rows[int(position)] = row.id
        self._emitter.emit(
            "agent_completed",
            f"{role_name(role_id)}: {summary}",
            agent_id=role_id,
            step=open_step["step"],
            agent_execution_id=row.id,
            data={
                "agent_name": role_name(role_id),
                "agent_execution_id": str(row.id),
                "model": row.model,
                # The billable figure, not the uncached remainder: a step that
                # reports "2 input tokens" beside a 30,000-character prompt
                # teaches the user the wrong thing about what a run costs.
                "input_tokens": row.input_tokens
                + row.cache_creation_input_tokens
                + row.cache_read_input_tokens,
                "output_tokens": row.output_tokens,
                "cache_read_input_tokens": row.cache_read_input_tokens,
                "cost_usd": row.cost_usd,
                "duration_ms": row.duration_ms,
                "attempt": row.attempt,
                "summary": summary,
                "assets_produced": [],
            },
        )

    def on_role_failed(self, role_id: str, error: str) -> None:
        open_step = self._close()
        if open_step is None:
            self._emitter.emit("run_error", error, level=LogLevel.ERROR, agent_id=role_id)
            return
        row = self._persist_row(open_step, ExecutionStatus.FAILED, output_data=None, error=error)
        self._emitter.emit(
            "agent_failed",
            f"{role_name(role_id)}: {error}",
            level=LogLevel.ERROR,
            agent_id=role_id,
            step=open_step["step"],
            agent_execution_id=row.id,
            data={
                "agent_name": role_name(role_id),
                "agent_execution_id": str(row.id),
                "error": error,
                "attempt": row.attempt,
            },
        )

    # ------------------------------------------------------------ artifacts

    def on_knowledge(self, artifacts: KnowledgeArtifacts, reused: bool, version: int) -> None:
        self._emitter.emit(
            "knowledge_ready",
            f"Knowledge {'reused' if reused else 'compiled'}: "
            f"{len(artifacts.evidence.entries)} facts the copy may claim, "
            f"{len(artifacts.gaps.unanswered)} gap(s)",
            agent_id="knowledge_compiler",
            data={
                "reused": reused,
                "version": version,
                "evidence_count": len(artifacts.evidence.entries),
                "segments": [segment.name for segment in artifacts.audience.segments],
                "gaps": [gap.missing for gap in artifacts.gaps.unanswered],
                "voice_learned": artifacts.voice.learned,
                # What the compile could not use, and why. A thin ledger has
                # two very different causes - a business with little to say,
                # or a page whose quotes would not verify because the crawler
                # got a JavaScript shell - and they need opposite responses
                # from the user. These were written onto the artifacts and
                # read by nothing.
                "notes": list(artifacts.notes),
            },
        )

    def on_brief(self, brief: CampaignBrief) -> None:
        self._emitter.emit(
            "brief_ready",
            f"Campaign brief: {brief.promise or brief.interpretation}",
            agent_id="strategist",
            data={
                "reader": brief.reader,
                "reader_segment": brief.reader_segment,
                "promise": brief.promise,
                "arc": brief.arc,
                "emails": [
                    {
                        "position": item.position,
                        "job": item.job,
                        "single_idea": item.single_idea,
                        "objection": item.objection,
                        "evidence_ids": item.evidence_ids,
                        "must_not_say": item.must_not_say,
                        # The argument, not only the claim. `single_idea` is
                        # what the email asserts; these four are why anybody
                        # should care, and a timeline that shows the first
                        # without the others cannot say whether the brief was
                        # the problem.
                        "felt_need": item.felt_need,
                        "status_quo": item.status_quo,
                        "why_it_fails": item.why_it_fails,
                        "mechanism": item.mechanism,
                    }
                    for item in brief.emails
                ],
            },
        )

    def on_draft(self, position: int, attempt: int, email: Email) -> None:
        """Every draft the writer produced, in full, including the candidates
        that lost the bake-off.

        This hook existed and was not implemented, so the only trace a rewrite
        left was its subject line in a summary. That makes the one question
        worth asking about a run - what changed between attempt 2 and attempt
        3, and did it help - unanswerable from the timeline, which is where
        four rewrites can circle back to a draft that was already read and
        discarded without anybody noticing.
        """
        self._emitter.emit(
            "draft",
            f'Email {position}, draft {attempt}: "{email.subject}"',
            agent_id="email_writer",
            data={
                "position": position,
                "attempt": attempt,
                "subject": email.subject,
                "preview_text": email.preview_text,
                "greeting": email.greeting,
                "body": email.body,
                "call_to_action": email.call_to_action,
                "sign_off": email.sign_off,
                "postscript": email.postscript,
                "word_count": len(email.body.split()),
            },
        )

    def on_repair(self, position: int, repair: int, reason: str) -> None:
        self._emitter.emit(
            "repair",
            f"Email {position}: the draft could not be sent as written "
            f"(repair {repair}) - {reason}",
            level=LogLevel.WARNING,
            agent_id="email_writer",
            data={"position": position, "repair": repair, "reason": reason},
        )

    def on_gates(self, position: int, attempt: int, report: GateReport) -> None:
        if not report.issues:
            self._emitter.emit(
                "gates",
                f"Email {position}: every automatic check passed",
                level=LogLevel.DEBUG,
                agent_id="email_writer",
                data={"position": position, "attempt": attempt, "passed": True},
            )
            return
        self._emitter.emit(
            "gates",
            f"Email {position}: {len(report.blocking)} automatic check(s) failed - "
            + "; ".join(issue.detail for issue in report.blocking[:2]),
            level=LogLevel.WARNING if report.blocking else LogLevel.DEBUG,
            agent_id="email_writer",
            data={
                "position": position,
                "attempt": attempt,
                "passed": report.passed,
                "issues": [
                    {"gate": issue.gate, "detail": issue.detail, "severity": issue.severity.value}
                    for issue in report.issues
                ],
            },
        )

    def on_read(self, position: int, attempt: int, read: PanelRead) -> None:
        primary = read.primary
        # Mapped onto the "review" event the live view already understands:
        # a cold reader's pull is the closest thing this architecture has to a
        # conversion score, and it is a far better one.
        #
        # `readers` carries the whole panel. The flat fields beside it are one
        # reader's answers and are kept for the timeline reducer that already
        # reads them; a run with three readers used to report the panel's
        # score next to the first reader's verdict, and drop the other two
        # entirely - which is the variance the panel is bought for.
        self._emitter.emit(
            "review",
            (
                f"Email {position} read cold: {read.verdict_line()}"
                if not read.understood
                else f"Email {position} read cold: {read.pull:.0f}/10 - {read.verdict_line()}"
            ),
            agent_id="blind_reader",
            data={
                "approved": read.landed,
                "conversion_score": round(read.pull),
                # Whether the panel could say what the email sold, beside the
                # score rather than folded into it. A timeline row showing
                # "3/10" for copy nobody could decode reports the wrong
                # problem: the number is an estimate of what people do with an
                # email they understood.
                "understood": read.understood,
                "summary": primary.what_it_sells,
                "issues": primary.fixes,
                "position": position,
                "attempt": attempt,
                "biggest_doubt": primary.biggest_doubt,
                "stopped_at": primary.stopped_at,
                "readers": [
                    {
                        "persona": item.persona,
                        "reported": item.reported,
                        "opened": item.opened,
                        "pull": item.pull,
                        "would_act": item.would_act,
                        "what_it_sells": item.what_it_sells,
                        "understood": item.understood,
                        "biggest_doubt": item.biggest_doubt,
                        "stopped_at": item.stopped_at,
                        "fixes": item.fixes,
                    }
                    for item in read.reads
                ],
            },
        )

    def on_critique(self, position: int, attempt: int, critique: Critique) -> None:
        self._emitter.emit(
            "critique",
            f"Email {position}: critic says {critique.verdict}"
            + (f" - {critique.summary}" if critique.summary else ""),
            agent_id="conversion_critic",
            data={
                "position": position,
                "attempt": attempt,
                "verdict": critique.verdict,
                "brief_drift": critique.brief_drift,
                "unspent_evidence": critique.unspent_evidence,
                "critique_summary": critique.summary,
                "edits": [
                    {
                        "line": edit.line,
                        "problem": edit.problem,
                        "fix": edit.fix,
                        "severity": edit.severity,
                    }
                    for edit in critique.edits
                ],
            },
        )

    def on_email_accepted(self, position: int, version: EmailVersion) -> None:
        self._emitter.emit(
            "email_ready",
            f'Email {position} ready: "{version.email.subject}" ({version.describe()})',
            agent_id="email_writer",
            data={
                "position": position,
                "subject": version.email.subject,
                "pull": version.read.pull,
                "attempts": version.attempt,
                "clean": not version.gates.blocking,
            },
        )

    def on_sequence(self, report: SequenceReport) -> None:
        self._emitter.emit(
            "sequence_review",
            report.render(),
            agent_id="sequence_reviewer",
            data={
                "passed": report.passed,
                "rework": {str(key): value for key, value in report.rework.items()},
                "summary": report.verdict.summary,
            },
        )

    def on_report(self, report: CampaignReport) -> None:
        self._emitter.emit(
            "campaign_report",
            report.render(),
            data={
                "delivered": report.delivered,
                "promised": report.promised,
                "average_pull": round(report.average_pull, 1),
                "contract_violations": report.contract_violations,
                "limiting_gaps": report.limiting_gaps,
                "below_floor": [line.position for line in report.below_floor],
                "what_would_help_most": report.what_would_help_most,
            },
        )

    # ------------------------------------------------------------- internals

    def _close(self) -> dict[str, Any] | None:
        open_step, self._open = self._open, None
        return open_step

    def _persist_row(
        self,
        open_step: dict[str, Any],
        status: ExecutionStatus,
        output_data: dict[str, Any] | None,
        error: str | None,
    ) -> AgentExecution:
        calls, self._calls = self._calls, []
        role_id = open_step["role_id"]
        return self._orchestrator._agent_executions.create(
            AgentExecution(
                campaign_execution_id=self._execution.id,
                agent_id=role_id,
                agent_name=role_name(role_id),
                sequence_order=open_step["step"],
                status=status,
                input_data={"label": open_step["label"], **open_step["data"]},
                output_data=output_data,
                error_message=error,
                started_at=open_step["started_at"],
                completed_at=datetime.now(UTC),
                model=calls[-1].model if calls else None,
                input_tokens=sum(call.input_tokens for call in calls),
                output_tokens=sum(call.output_tokens for call in calls),
                cache_creation_input_tokens=sum(
                    call.cache_creation_input_tokens for call in calls
                ),
                cache_read_input_tokens=sum(call.cache_read_input_tokens for call in calls),
                cost_usd=round(sum(call.cost_usd for call in calls), 6),
                duration_ms=sum(call.duration_ms for call in calls),
                attempt=self.attempts.get(role_id, 1),
            )
        )


class CampaignOrchestrator:
    """Thin persistence adapter around the campaign pipeline.

    It makes NO decisions about what runs: it creates the execution row, hands
    the request and the business's knowledge to the pipeline, persists every
    role run, deliverable and log line, and finalizes the execution row. All
    the reasoning lives in app.marketing.pipeline.

    `create_execution` and `execute` are split so a caller that needs the
    execution row back immediately (the async /start endpoint - see
    app.orchestration.execution_manager) can do so without waiting for the run
    to finish; `run` is the two combined, for direct/synchronous callers such
    as the test suite.
    """

    def __init__(self, session: Session, ai_provider: AIProvider) -> None:
        self._session = session
        self._campaign_executions = CampaignExecutionRepository(session)
        self._agent_executions = AgentExecutionRepository(session)
        self._generated_assets = GeneratedAssetRepository(session)
        self._logs = ExecutionLogRepository(session)
        self._ai_provider = ai_provider

    def _usable_after_close(self, execution: CampaignExecution) -> CampaignExecution:
        """Reload an execution the caller will keep using once this session is
        gone.

        Emitting an event writes a log row, and that commit expires every
        other instance in the session - including the execution being
        returned. Callers such as execution_manager.launch read its id after
        the `with Session(...)` block has closed, where an expired instance
        can no longer refresh itself and raises DetachedInstanceError.
        """
        self._session.refresh(execution)
        return execution

    def _emitter_for(self, execution_id: UUID) -> ExecutionEventEmitter:
        return ExecutionEventEmitter(self._logs, execution_id)

    def create_execution(self, campaign: Campaign) -> CampaignExecution:
        execution = self._campaign_executions.create(
            CampaignExecution(
                campaign_id=campaign.id,
                status=ExecutionStatus.RUNNING,
                started_at=datetime.now(UTC),
            )
        )
        self._emitter_for(execution.id).emit(
            "execution_started",
            f"Request: {campaign.request}",
            data={"campaign_id": str(campaign.id), "request": campaign.request},
        )
        return self._usable_after_close(execution)

    async def run(
        self, campaign: Campaign, cancel_token: CancellationToken | None = None
    ) -> CampaignExecution:
        execution = self.create_execution(campaign)
        return await self.execute(campaign, execution, cancel_token=cancel_token)

    async def execute(
        self,
        campaign: Campaign,
        execution: CampaignExecution,
        cancel_token: CancellationToken | None = None,
    ) -> CampaignExecution:
        emitter = self._emitter_for(execution.id)
        observer = _PersistenceObserver(self, execution, emitter)
        policy = resolve_policy(
            (campaign.policy or {}).get("preset"),
            {k: v for k, v in (campaign.policy or {}).items() if k != "preset"} or None,
        )
        events = EventBus()
        _bridge_runtime_events(events, emitter)

        session = ModelSession(
            provider=self._ai_provider,
            prompt_engine=get_prompt_engine(PROMPTS_DIR),
            events=events,
            model_router=ModelRouter(_resolve_overrides(policy, campaign)),
            execution_id=str(execution.id),
            on_call=observer.record_call,
        )
        pipeline = EmailCampaignPipeline(
            session=session,
            knowledge=_DbKnowledgeGateway(self._session, campaign),
            policy=policy,
            observer=observer,
            cancel_token=cancel_token,
            deadline=(
                time.monotonic() + policy.max_duration_seconds
                if policy.max_duration_seconds is not None
                else None
            ),
        )
        request = CampaignRequest(
            name=campaign.name,
            request=campaign.request,
            product_description=campaign.product_description,
            product_url=campaign.product_url,
            target_market=campaign.target_market,
            goals=campaign.goals,
            sender_name=campaign.sender_name or "",
            sender_role=campaign.sender_role or "",
        )

        try:
            result = await pipeline.run(request)
        except Exception as exc:
            logger.exception("campaign run crashed")
            emitter.current_step = None
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(exc)
            execution.completed_at = datetime.now(UTC)
            self._campaign_executions.update(execution)
            emitter.emit(
                "execution_finished",
                f"Campaign run failed: {exc}",
                level=LogLevel.ERROR,
                data={"status": "failed", "error": str(exc)},
            )
            broker.close(execution.id)
            return self._usable_after_close(execution)

        emitter.current_step = None
        self._persist_assets(campaign, execution, result, observer)
        self._finalize(execution, result)
        emitter.emit(
            "execution_finished",
            f"Campaign run finished: {result.status}",
            data={
                "status": execution.status.value,
                "run_status": result.status,
                "estimated_cost_usd": execution.estimated_cost_usd,
                "delivered": len(result.outcomes),
            },
        )
        broker.close(execution.id)
        return self._usable_after_close(execution)

    # ------------------------------------------------------------- internals

    def _persist_assets(
        self,
        campaign: Campaign,
        execution: CampaignExecution,
        result: CampaignRunResult,
        observer: _PersistenceObserver,
    ) -> None:
        """One row per email, written once the run is over.

        Deliberately not written as each draft lands: an email is rewritten up
        to three times and reworked again by the sequence pass, and persisting
        every version as a deliverable would hand the user four copies of the
        same email to choose between. The versions are in the timeline; the
        clipboard gets the one that won.
        """
        fallback = next(iter(observer.writer_rows.values()), None)
        tier, brand = self._presentation(campaign)
        for outcome in result.outcomes:
            email: Email = outcome.email
            agent_execution_id = observer.writer_rows.get(email.position, fallback)
            if agent_execution_id is None:
                logger.warning("no agent execution row to attach email %d to", email.position)
                continue
            self._generated_assets.create(
                GeneratedAsset(
                    campaign_execution_id=execution.id,
                    agent_execution_id=agent_execution_id,
                    asset_type=AssetType.EMAIL,
                    title=email.subject,
                    content=render_email(email),
                    content_html=_html_or_none(email, tier, brand),
                    position=email.position,
                    asset_metadata={
                        **email.model_dump(mode="json"),
                        "pull": outcome.best.read.pull,
                        "revisions": len(outcome.versions) - 1,
                        "single_idea": outcome.brief.single_idea,
                        "evidence_ids": outcome.brief.evidence_ids,
                        "tier": tier.value,
                    },
                )
            )

    def _presentation(self, campaign: Campaign) -> tuple[EmailTier, BrandStyle]:
        """How this campaign's emails should look.

        Plain by default, and deliberately: these are mostly cold sales
        sequences, where a branded template reads as a mailshot, scores worse
        with filters and converts worse than a message that looks like it came
        from a person. A campaign asks for the branded tier explicitly, and
        only a campaign attached to a brand has anything to brand it with.

        The CTA URL is the one field here the campaign may override, because
        it is the one that changes per campaign: a launch points at the launch
        page and a cart recovery points at the cart. The brand's own website
        is the fallback, which is right far more often than nothing is - and
        nothing is still the answer when neither exists, since the renderer
        would otherwise draw a button to a page that does not exist.
        """
        requested = (campaign.policy or {}).get("email_tier")
        tier = EmailTier.BRANDED if requested == EmailTier.BRANDED else EmailTier.PLAIN
        if campaign.brand_id is None:
            return tier, BrandStyle(cta_url=campaign.cta_url or "")
        brand = BrandRepository(self._session).get(campaign.brand_id)
        if brand is None:
            return tier, BrandStyle(cta_url=campaign.cta_url or "")
        return tier, BrandStyle(
            name=brand.name,
            logo_url=brand.logo_url or "",
            primary_color=brand.primary_color or BrandStyle.primary_color,
            footer_lines=tuple(brand.footer_lines or ()),
            cta_url=campaign.cta_url or brand.website_url or "",
            unsubscribe_url=brand.unsubscribe_url or "",
        )

    def _finalize(self, execution: CampaignExecution, result: CampaignRunResult) -> None:
        if result.status == "cancelled":
            execution.status = ExecutionStatus.CANCELLED
            execution.error_message = result.abort_reason
        elif result.status in _DELIVERING_STATUSES and result.delivered:
            execution.status = ExecutionStatus.COMPLETED
            # A degraded run still delivered: keep the caveat, drop any stale
            # failure the startup reaper may have written onto this row.
            execution.error_message = (
                result.abort_reason if result.status != "completed" else None
            )
        elif result.status == "needs_input":
            # Not a crash and not a delivery: the run stopped on purpose,
            # before spending anything, because the material could not carry a
            # campaign. There is no lifecycle status for "asked a question", so
            # it lands on FAILED - but the message is the questions, not a
            # stack trace, and `report.questions` carries them structured.
            execution.status = ExecutionStatus.FAILED
            execution.error_message = "\n".join(
                [result.abort_reason or "", *result.report.questions]
            ).strip()
        else:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = (
                result.abort_reason or f"Campaign run ended: {result.status}"
            )

        execution.completed_at = datetime.now(UTC)
        execution.result = {
            "run_status": result.status,
            "report": result.report.model_dump(mode="json"),
            "brief": result.brief.model_dump(mode="json") if result.brief else None,
            "knowledge_version": result.artifacts.version if result.artifacts else 0,
        }
        # Every input token the run consumed, cached input included - that is
        # what the user's quota paid for, and recording only the uncached
        # remainder is what made every earlier run look ~40% cheaper than it
        # was. Cost is summed per call, where the provider's own figure was
        # already preferred over our price table (see usage_cost_usd).
        execution.total_input_tokens = result.usage.billable_input_tokens
        execution.total_output_tokens = result.usage.output_tokens
        execution.total_cache_read_tokens = result.usage.cache_read_input_tokens
        execution.estimated_cost_usd = round(result.usage.cost_usd, 4)
        self._campaign_executions.update(execution)


def _html_or_none(email: Email, tier: EmailTier, brand: BrandStyle) -> str | None:
    """The rendered email, or nothing at all.

    Rendering is presentation, and the deliverable is `content` - the text the
    user pastes. A campaign that spent thirteen minutes and real money writing
    three good emails must not be reported as failed because a logo URL had a
    character in it that something did not like. Anything that goes wrong here
    costs the HTML and nothing else.
    """
    try:
        rendered = render_html(email, tier, brand)
    except Exception:
        logger.warning("could not render email %d as HTML", email.position, exc_info=True)
        return None
    size = len(rendered.encode("utf-8"))
    if size > MAX_EMAIL_BYTES:
        # Gmail clips past this and hides everything below the fold, which in
        # an email is usually the call to action.
        logger.warning(
            "email %d renders to %d bytes, past the %d clipping limit - keeping text only",
            email.position,
            size,
            MAX_EMAIL_BYTES,
        )
        return None
    return rendered


def _resolve_overrides(policy: ExecutionPolicy, campaign: Campaign) -> dict[str, str]:
    """The model map this run routes on: the preset's, then the operator's.

    A plain merge is wrong in one case, and it is the case the picker exists
    for. `ModelRouter` checks an exact role id before it looks at the wildcard,
    and the `maximum` preset ships per-role overrides for the five craft roles.
    So an operator who chose "every agent -> GPT" on that preset would get a
    run where the strategist, writer, critic, sequence reviewer and subject
    writer all quietly stayed on Opus - the five roles they most likely meant.
    Nothing would say so; the picker would show GPT and the receipt would show
    Claude.

    A wildcard the operator set is a statement about the whole run, so it
    displaces the preset's suggestions entirely. Their own per-agent pins are
    applied on top and still win, which is exactly what the panel promises.
    """
    overrides: dict[str, str] = {} if WILDCARD_ROLE in (
        campaign.model_overrides or {}
    ) else dict(policy.model_overrides)
    overrides.update(campaign.model_overrides or {})
    return overrides


def _bridge_runtime_events(events: EventBus, emitter: ExecutionEventEmitter) -> None:
    """Forward the model session's own event bus onto the execution's stream.

    These are the events that fill the long silence of a single `generate()`
    call, which is most of what a campaign spends its time on. Everything here
    is progress, not history: DEBUG level, so the activity log stays readable
    while the live view still gets a heartbeat.
    """

    def on_model_call_started(event: ModelCallStarted) -> None:
        emitter.emit(
            "model_call_started",
            f"Sent {event.prompt_chars:,} characters to {event.model} - waiting for the answer",
            level=LogLevel.DEBUG,
            agent_id=event.agent_id,
            data={"model": event.model, "prompt_chars": event.prompt_chars},
        )

    def on_model_call_retried(event: ModelCallRetried) -> None:
        # WARNING, not DEBUG: everything else on this bridge is progress a
        # healthy run also produces, and this is the one line that says the
        # run is in trouble. A retry that scrolls past with the heartbeat is
        # a retry nobody sees.
        emitter.emit(
            "model_call_retried",
            f"{event.model} did not answer (attempt {event.attempt}: {event.error}) - "
            "sending it again",
            level=LogLevel.WARNING,
            agent_id=event.agent_id,
            data={"model": event.model, "attempt": event.attempt, "error": event.error},
        )

    def on_model_call_finished(event: ModelCallFinished) -> None:
        emitter.emit(
            "model_call_finished",
            f"{event.model} answered with {event.response_chars:,} characters "
            f"in {event.duration_ms / 1000:.1f}s "
            f"({event.billable_input_tokens:,} in / {event.output_tokens:,} out)",
            level=LogLevel.DEBUG,
            agent_id=event.agent_id,
            data={
                "model": event.model,
                "input_tokens": event.billable_input_tokens,
                "output_tokens": event.output_tokens,
                "cache_read_input_tokens": event.cache_read_input_tokens,
                "cost_usd": round(event.cost_usd, 6),
                "duration_ms": event.duration_ms,
                "response_chars": event.response_chars,
            },
        )

    events.subscribe(ModelCallStarted, on_model_call_started)
    events.subscribe(ModelCallRetried, on_model_call_retried)
    events.subscribe(ModelCallFinished, on_model_call_finished)
