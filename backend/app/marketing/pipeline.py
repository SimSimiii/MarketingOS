"""The campaign pipeline: three phases, orchestrated in code.

There is no LLM director any more, and removing it is the central change of
this design. The old one spent a model call per step deciding which specialist
to run next, out of a catalog whose correct order was fixed by data
dependencies and was already written down, in prose, inside the director's own
prompt. An LLM interpreting an if-statement is not orchestration; it is an
expensive, stochastic re-derivation of a decision that was never open. It also
came with its own failure mode - invalid decisions - and the machinery to
survive that failure mode was a meaningful fraction of the old codebase.

What is left is a state machine. Knowledge is compiled (or reused), a brief is
written, each email is crafted, the sequence is read as a sequence, and the
result is checked against the contract that was parsed out of the user's
sentence before anything ran. Every model call in the run either distills
knowledge, decides strategy, writes copy, or judges copy. None of them route.

The guards from the old director are kept in spirit: budgets and deadlines are
checked between steps, never mid-call, so a stopped run always leaves a
consistent, fully persisted state rather than a half-written email.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.compiler import ROLE_ID as COMPILER_ROLE
from app.knowledge.compiler import KnowledgeCompiler
from app.knowledge.corpus import SourceCorpus
from app.knowledge.ledger import EvidenceIndex
from app.knowledge.store import StoredArtifacts
from app.marketing.briefs import CampaignBrief
from app.marketing.cancellation import CancellationToken
from app.marketing.contract import DeliverableContract, check_contract, parse_contract
from app.marketing.craft import CraftLoop, EmailOutcome
from app.marketing.critic import ConversionCritic
from app.marketing.email_copy import Email
from app.marketing.exceptions import CampaignError
from app.marketing.observer import RunObserver
from app.marketing.policy import ExecutionPolicy
from app.marketing.preflight import assess
from app.marketing.reader import PULL_THRESHOLD, BlindReader, personas_for
from app.marketing.report import CampaignReport, EmailReportLine
from app.marketing.request import CampaignRequest
from app.marketing.sequence import ROLE_ID as SEQUENCE_ROLE
from app.marketing.sequence import SequenceReport, SequenceReviewer
from app.marketing.strategist import ROLE_ID as STRATEGIST_ROLE
from app.marketing.strategist import Strategist
from app.marketing.writer import EmailWriter
from app.runtime.model_session import ModelSession, Usage

logger = logging.getLogger("marketingos.marketing")

RunStatus = Literal[
    "completed", "degraded", "failed", "cancelled", "timed_out", "budget_exhausted"
]

_GUARD_MESSAGES: dict[str, str] = {
    "cancelled": "Cancelled by user request.",
    "timed_out": "Execution exceeded its maximum run time.",
    "budget_exhausted": "Execution exceeded its token budget.",
}


class KnowledgeGateway(ABC):
    """Where the pipeline gets a business's material and compiled knowledge.

    An interface rather than a database call so the pipeline can be run - and
    tested - without one. The orchestrator implements it over the artifact
    store; a test implements it over a list of strings.
    """

    @abstractmethod
    def corpus(self) -> SourceCorpus: ...

    @abstractmethod
    def fingerprint(self) -> str: ...

    @abstractmethod
    def load(self) -> StoredArtifacts | None: ...

    @abstractmethod
    def save(self, artifacts: KnowledgeArtifacts, fingerprint: str) -> StoredArtifacts: ...

    def prior_learnings(self) -> str:
        """What earlier campaigns for this business found out. Empty is fine."""
        return ""


@dataclass
class CampaignRunResult:
    status: RunStatus = "failed"
    artifacts: KnowledgeArtifacts | None = None
    brief: CampaignBrief | None = None
    outcomes: list[EmailOutcome] = field(default_factory=list)
    sequence: SequenceReport | None = None
    report: CampaignReport = field(default_factory=CampaignReport)
    usage: Usage = field(default_factory=Usage)
    abort_reason: str | None = None

    @property
    def emails(self) -> list[Email]:
        return [outcome.email for outcome in self.outcomes]

    @property
    def delivered(self) -> bool:
        return bool(self.outcomes)


class EmailCampaignPipeline:
    def __init__(
        self,
        *,
        session: ModelSession,
        knowledge: KnowledgeGateway,
        policy: ExecutionPolicy,
        observer: RunObserver | None = None,
        cancel_token: CancellationToken | None = None,
        deadline: float | None = None,
    ) -> None:
        self._session = session
        self._knowledge = knowledge
        self._policy = policy
        self._observer = observer or RunObserver()
        self._cancel_token = cancel_token
        self._deadline = deadline

    async def run(self, request: CampaignRequest) -> CampaignRunResult:
        result = CampaignRunResult(usage=self._session.usage)
        contract = parse_contract(request.request)
        self._observer.on_phase(
            "contract",
            f"Read the request as {contract.count} email(s)"
            + (" - the user said so" if contract.count_is_explicit else " - not specified"),
            {"count": contract.count, "explicit": contract.count_is_explicit},
        )

        try:
            artifacts, corpus = await self._phase_knowledge(result)
            if (guard := self._guard()) is not None:
                return self._stopped(request, contract, result, guard)

            # Said out loud before the strategy is decided rather than
            # discovered on the receipt: what the copy is allowed to argue
            # from constrains the campaign, and no rewrite later on can add a
            # proof the material never contained.
            posture = assess(artifacts)
            self._observer.on_phase(
                "proof",
                posture.summary(),
                {
                    "proof": len(posture.proof),
                    "checkable": len(posture.checkable),
                    "asks": posture.asks[:1],
                },
            )

            brief = await self._phase_strategy(request, artifacts, corpus, contract, result)
            if (guard := self._guard()) is not None:
                return self._stopped(request, contract, result, guard)

            guard = await self._phase_craft(request, brief, artifacts, corpus, result)
            if guard is not None:
                return self._stopped(request, contract, result, guard)

            await self._phase_sequence(request, brief, artifacts, corpus, result)
        except CampaignError as exc:
            logger.warning("pipeline: run failed - %s", exc)
            self._observer.on_role_failed(exc.details.get("role", "pipeline"), str(exc))
            result.status = "failed"
            result.abort_reason = str(exc)
            result.report = self._build_report(request, contract, result)
            self._observer.on_report(result.report)
            return result

        result.report = self._build_report(request, contract, result)
        result.status = "completed" if result.report.healthy else "degraded"
        self._observer.on_report(result.report)
        below = result.report.below_floor
        self._observer.on_phase(
            "finished",
            f"{result.report.delivered} email(s) ready - average cold-reader pull "
            f"{result.report.average_pull:.1f}/10"
            + (
                f" - {len(below)} still under the {PULL_THRESHOLD}/10 floor when the loop "
                "stopped rewriting"
                if below
                else ""
            ),
            {"status": result.status, "below_floor": [line.position for line in below]},
        )
        return result

    # ----------------------------------------------------------- phase zero

    async def _phase_knowledge(
        self, result: CampaignRunResult
    ) -> tuple[KnowledgeArtifacts, SourceCorpus]:
        corpus = self._knowledge.corpus()
        fingerprint = self._knowledge.fingerprint()
        stored = self._knowledge.load()

        if (
            stored is not None
            and stored.fingerprint == fingerprint
            and not self._policy.force_recompile
        ):
            # Nothing the user gave us has changed since this was compiled.
            # Re-reading their whole site to reach the same conclusions is the
            # most expensive way to learn nothing.
            self._observer.on_phase(
                "knowledge",
                f"Reusing what we already know about this business "
                f"(version {stored.version}, {len(stored.artifacts.evidence.entries)} facts)",
                {"reused": True, "version": stored.version},
            )
            self._observer.on_knowledge(stored.artifacts, True, stored.version)
            result.artifacts = stored.artifacts
            return stored.artifacts, corpus

        # An empty corpus costs no model call at all, so it gets no step of its
        # own - a zero-token "Knowledge Compiler" row in the timeline would be
        # work the run never did.
        reading = not corpus.is_empty
        if reading:
            self._observer.on_role_started(
                COMPILER_ROLE,
                f"Reading {len(corpus.documents)} document(s)",
                {"documents": len(corpus.documents)},
            )
        else:
            self._observer.on_phase(
                "knowledge",
                "The user provided no material to read - the copy will have nothing "
                "specific to say",
                {"documents": 0},
            )
        artifacts = await KnowledgeCompiler(self._session).compile(
            corpus,
            on_progress=lambda stage, message: self._observer.on_phase(
                "knowledge", message, {"stage": stage}
            ),
        )
        saved = self._knowledge.save(artifacts, fingerprint)
        if reading:
            self._observer.on_role_finished(
                COMPILER_ROLE,
                f"{len(artifacts.evidence.entries)} facts, {len(artifacts.audience.segments)} "
                f"segment(s), {len(artifacts.gaps.unanswered)} gap(s)",
                {"version": saved.version, "evidence": len(artifacts.evidence.entries)},
            )
        self._observer.on_knowledge(saved.artifacts, False, saved.version)
        result.artifacts = saved.artifacts
        return saved.artifacts, corpus

    # ------------------------------------------------------------ phase one

    async def _phase_strategy(
        self,
        request: CampaignRequest,
        artifacts: KnowledgeArtifacts,
        corpus: SourceCorpus,
        contract: DeliverableContract,
        result: CampaignRunResult,
    ) -> CampaignBrief:
        self._observer.on_role_started(
            STRATEGIST_ROLE, "Deciding what this campaign says, and in what order"
        )
        brief = await Strategist(self._session).build(
            request=request,
            artifacts=artifacts,
            corpus=corpus,
            contract=contract,
            prior_learnings=self._knowledge.prior_learnings(),
        )
        result.brief = brief
        self._observer.on_brief(brief)
        self._observer.on_role_finished(
            STRATEGIST_ROLE,
            f"{len(brief.emails)} email(s) to {brief.reader or 'the target reader'}",
            {"emails": [item.summary() for item in brief.emails]},
        )

        # Announced rather than left implicit: who grades the copy decides
        # what every rewrite in the run is aiming at, and it is the one
        # decision here that used to be made by list order.
        segment = artifacts.audience.match(brief.reader_segment, brief.reader)
        fallback = artifacts.audience.primary()
        self._observer.on_phase(
            "strategy",
            "Drafts will be read cold by: "
            + (
                segment.name
                if segment is not None
                else f"{fallback.name} (the brief named no segment we know)"
                if fallback is not None
                else "a busy professional - the material named no audience at all"
            ),
            {
                "segment": segment.name if segment is not None else "",
                "matched": segment is not None,
            },
        )
        return brief

    # ------------------------------------------------------------ phase two

    async def _phase_craft(
        self,
        request: CampaignRequest,
        brief: CampaignBrief,
        artifacts: KnowledgeArtifacts,
        corpus: SourceCorpus,
        result: CampaignRunResult,
    ) -> str | None:
        loop = self._craft_loop(artifacts, corpus, brief)
        accepted: list[Email] = []

        for email_brief in brief.emails:
            if (guard := self._guard()) is not None:
                # Stop between emails, never inside one: a half-written email
                # is worse than one fewer email.
                return guard
            self._observer.on_phase(
                "craft",
                f"Email {email_brief.position} of {len(brief.emails)}: "
                f"{email_brief.single_idea or email_brief.job}",
                {"position": email_brief.position},
            )
            outcome = await loop.craft(
                brief=email_brief, campaign=brief, request=request, previous=accepted
            )
            result.outcomes.append(outcome)
            accepted.append(outcome.email)
        return None

    # ---------------------------------------------------------- phase three

    async def _phase_sequence(
        self,
        request: CampaignRequest,
        brief: CampaignBrief,
        artifacts: KnowledgeArtifacts,
        corpus: SourceCorpus,
        result: CampaignRunResult,
    ) -> None:
        if len(result.outcomes) < 2 or self._policy.max_sequence_reworks == 0:
            return
        if self._guard() is not None:
            return

        self._observer.on_role_started(
            SEQUENCE_ROLE, f"Reading all {len(result.outcomes)} emails as one sequence"
        )
        report = await SequenceReviewer(self._session).review(
            result.emails, brief, arc_read=self._policy.sequence_pass
        )
        result.sequence = report
        self._observer.on_sequence(report)
        self._observer.on_role_finished(
            SEQUENCE_ROLE,
            "The sequence holds together"
            if report.passed
            else f"{len(report.rework)} email(s) need reworking",
            {"passed": report.passed},
        )
        if report.passed:
            return

        loop = self._craft_loop(artifacts, corpus, brief)
        reworked = 0
        for position in sorted(report.rework):
            if reworked >= self._policy.max_sequence_reworks or self._guard() is not None:
                break
            outcome = next(
                (item for item in result.outcomes if item.brief.position == position), None
            )
            if outcome is None:
                continue
            self._observer.on_phase(
                "sequence",
                f"Reworking email {position}: {'; '.join(report.rework[position])}",
                {"position": position},
            )
            others = [item.email for item in result.outcomes if item.brief.position != position]
            await loop.rework(
                outcome=outcome,
                campaign=brief,
                request=request,
                previous=others,
                instruction=(
                    "Read as part of the whole sequence, this email has a problem the other "
                    f"emails create:\n{report.instruction_for(position)}"
                ),
            )
            reworked += 1

    # ------------------------------------------------------------- internals

    def _craft_loop(
        self, artifacts: KnowledgeArtifacts, corpus: SourceCorpus, brief: CampaignBrief
    ) -> CraftLoop:
        return CraftLoop(
            writer=EmailWriter(self._session, self._observer),
            reader=BlindReader(self._session),
            critic=ConversionCritic(self._session) if self._policy.critic_enabled else None,
            artifacts=artifacts,
            evidence=EvidenceIndex(artifacts.evidence, corpus.text),
            personas=personas_for(
                artifacts.audience,
                artifacts.audience.match(brief.reader_segment, brief.reader),
                panel=self._policy.reader_panel,
            ),
            merge_fields=self._policy.merge_fields,
            max_revisions=self._policy.max_revisions,
            candidates=self._policy.draft_candidates,
            observer=self._observer,
        )

    def _guard(self) -> str | None:
        if self._cancel_token is not None and self._cancel_token.is_cancelled:
            return "cancelled"
        if self._deadline is not None and time.monotonic() >= self._deadline:
            return "timed_out"
        budget = self._policy.max_total_tokens
        if budget is not None and self._session.usage.total_tokens >= budget:
            return "budget_exhausted"
        return None

    def _stopped(
        self,
        request: CampaignRequest,
        contract: DeliverableContract,
        result: CampaignRunResult,
        guard: str,
    ) -> CampaignRunResult:
        """A run that ran out of time, budget or patience still hands over
        whatever is finished. Degrading to "here are three of the five, and
        here is why" beats failing a campaign that has minutes of good work
        in it."""
        result.status = guard  # type: ignore[assignment]
        result.abort_reason = _GUARD_MESSAGES.get(guard, guard)
        result.report = self._build_report(request, contract, result)
        self._observer.on_report(result.report)
        self._observer.on_phase("stopped", result.abort_reason, {"status": guard})
        return result

    def _build_report(
        self,
        request: CampaignRequest,
        contract: DeliverableContract,
        result: CampaignRunResult,
    ) -> CampaignReport:
        lines = [
            EmailReportLine(
                position=outcome.brief.position,
                subject=outcome.email.subject,
                single_idea=outcome.brief.single_idea,
                pull=outcome.best.read.pull,
                revisions=len(outcome.versions) - 1,
                clean=not outcome.best.gates.blocking,
                landed=outcome.best.read.landed,
                rewrites_stopped_helping=outcome.stopped_early,
                read_reported=outcome.best.read.has_verdict,
                evidence_spent=outcome.brief.evidence_ids,
                unresolved=[issue.detail for issue in outcome.best.gates.blocking],
            )
            for outcome in result.outcomes
        ]
        violations = check_contract(contract, len(result.outcomes))
        gaps = result.artifacts.gaps.unanswered if result.artifacts else []
        posture = assess(result.artifacts) if result.artifacts else None
        return CampaignReport(
            request=request.request,
            delivered=len(result.outcomes),
            promised=contract.count,
            contract_violations=[violation.detail for violation in violations],
            emails=lines,
            limiting_gaps=[f"{gap.missing} - {gap.impact}" for gap in gaps],
            what_would_help_most=posture.asks[0] if posture and posture.asks else "",
            sequence_summary=result.sequence.verdict.summary if result.sequence else "",
            knowledge_version=result.artifacts.version if result.artifacts else 0,
            notes=[result.abort_reason] if result.abort_reason else [],
        )
