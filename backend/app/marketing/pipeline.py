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
from app.market.demand import DemandMap
from app.market.positioning import PositioningMap
from app.marketing.briefs import CampaignBrief
from app.marketing.cancellation import CancellationToken
from app.marketing.contract import DeliverableContract, check_contract, parse_contract
from app.marketing.craft import CraftLoop, EmailOutcome
from app.marketing.critic import ConversionCritic
from app.marketing.email_copy import Email
from app.marketing.exceptions import CampaignError
from app.marketing.observer import RunObserver
from app.marketing.policy import ExecutionPolicy
from app.marketing.preflight import ProofPosture, assess
from app.marketing.reader import PULL_THRESHOLD, BlindReader, personas_for
from app.marketing.report import CampaignReport, EmailReportLine, ReaderVerdict
from app.marketing.request import CampaignRequest
from app.marketing.sequence import ROLE_ID as SEQUENCE_ROLE
from app.marketing.sequence import SequenceReport, SequenceReviewer
from app.marketing.strategist import ROLE_ID as STRATEGIST_ROLE
from app.marketing.strategist import Strategist
from app.marketing.subject_lines import SubjectBakeOff
from app.marketing.tournament import PreferenceJudge
from app.marketing.writer import EmailWriter
from app.runtime.exceptions import ModelRuntimeError
from app.runtime.model_session import ModelSession, Usage

logger = logging.getLogger("marketingos.marketing")

RunStatus = Literal[
    "completed",
    "degraded",
    "failed",
    "cancelled",
    "timed_out",
    "budget_exhausted",
    "provider_unavailable",
    "needs_input",
]

_GUARD_MESSAGES: dict[str, str] = {
    "cancelled": "Cancelled by user request.",
    "timed_out": "Execution exceeded its maximum run time.",
    "budget_exhausted": "Execution exceeded its token budget.",
    "provider_unavailable": (
        "The model stopped answering and did not come back after several attempts. "
        "Everything finished before that point is below."
    ),
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

    def positioning(self) -> PositioningMap | None:
        """Where this business stands against its market, if anybody has read it.

        On the gateway rather than passed into `run` because it is the same
        kind of thing as the compiled artifacts: it belongs to the business,
        it outlives the campaign, and a pipeline running without a database
        should be able to answer "nobody has scanned this market" without a
        caller having to say so. None is a first-class answer here - see
        `PositioningMap.render_for_strategy`, which tells the strategist that
        it is writing blind rather than that the field is empty.
        """
        return None

    def demand(self) -> DemandMap | None:
        """Who the market says would buy this, if anybody has mapped it.

        Beside `positioning` and for the same reasons: it belongs to the
        business, it outlives the campaign, and None is a first-class answer -
        see `DemandMap.render_for_strategy`, which tells the strategist it is
        working from the company's own idea of its buyer rather than pretending
        the question was never asked.
        """
        return None

    def audience_choice(self) -> str:
        """The mapped segment this campaign was pointed at, or "" for none.

        Separate from `demand` because they answer different questions: one is
        what exists, the other is what this run was asked to do with it. The
        chosen segment is *already* at the head of the artifacts by the time
        the pipeline sees them (see `app.market.store.merge_audience`), so
        nothing downstream needs this - the strategist does, because the
        contrast between the buyer it was given and the ones it was not is
        what makes the choice legible.
        """
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
            if self._policy.require_proof and posture.nothing_to_argue_from:
                return self._needs_input(request, contract, result, posture)

            positioning = self._knowledge.positioning()
            if positioning is not None and not positioning.is_empty:
                self._observer.on_phase(
                    "market",
                    positioning.summary(),
                    {
                        "rivals": positioning.rivals_profiled,
                        "open_ground": [
                            str(reading.axis) for reading in positioning.open_ground
                        ],
                    },
                )

            demand = self._knowledge.demand()
            chosen = self._knowledge.audience_choice()
            if chosen:
                # Said out loud for the same reason the proof posture is: this
                # decides who every draft in the run is written to and graded
                # by, and a run whose audience was quietly swapped by a form
                # field is a run whose report nobody can read afterwards.
                mapped = demand.named(chosen) if demand is not None else None
                self._observer.on_phase(
                    "audience",
                    f"Written to {chosen}"
                    + (
                        f" - {round(mapped.fit * 100)}% of them are estimated to bite"
                        if mapped is not None
                        else " - which is not on this brand's audience map"
                    ),
                    {"segment": chosen, "mapped": mapped is not None},
                )

            brief = await self._phase_strategy(
                request, artifacts, corpus, contract, result, positioning, demand, chosen
            )
            if (guard := self._guard()) is not None:
                return self._stopped(request, contract, result, guard)

            guard = await self._phase_craft(
                request, brief, artifacts, corpus, result, positioning
            )
            if guard is not None:
                return self._stopped(request, contract, result, guard)

            await self._phase_sequence(request, brief, artifacts, corpus, result)
        except ModelRuntimeError as exc:
            # The provider stopped answering, after `ModelSession` had already
            # resent the call. Treated exactly like running out of time: stop
            # between steps, keep everything finished, say why.
            #
            # It reaches here at all because nothing else could catch it. This
            # is not a `CampaignError`, so before this the exception went
            # straight past the pipeline into the orchestrator's crash
            # handler - which persists no assets and no report, and threw
            # away every email the run had already written and paid for.
            logger.warning("pipeline: the provider stopped answering - %s", exc)
            self._observer.on_role_failed(str(exc.details.get("role", "pipeline")), str(exc))
            return self._stopped(request, contract, result, "provider_unavailable")
        except CampaignError as exc:
            logger.warning("pipeline: run failed - %s", exc)
            self._observer.on_role_failed(exc.details.get("role", "pipeline"), str(exc))
            # A failure that arrives with finished emails behind it is a
            # degraded run, not a failed one. Three good emails out of five
            # are three good emails, and reporting them under a red banner is
            # what teaches a user to distrust the badge on the runs that
            # really did fail.
            result.status = "degraded" if result.delivered else "failed"
            result.abort_reason = str(exc)
            result.report = self._build_report(request, contract, result)
            self._observer.on_report(result.report)
            self._observer.on_phase(
                "stopped", result.abort_reason, {"status": result.status}
            )
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
        positioning: PositioningMap | None = None,
        demand: DemandMap | None = None,
        chosen_segment: str = "",
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
            positioning=positioning,
            demand=demand,
            chosen_segment=chosen_segment,
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
        positioning: PositioningMap | None = None,
    ) -> str | None:
        loop = self._craft_loop(artifacts, corpus, brief, positioning)
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
        self,
        artifacts: KnowledgeArtifacts,
        corpus: SourceCorpus,
        brief: CampaignBrief,
        positioning: PositioningMap | None = None,
    ) -> CraftLoop:
        return CraftLoop(
            writer=EmailWriter(self._session, self._observer),
            reader=BlindReader(self._session),
            critic=ConversionCritic(self._session) if self._policy.critic_enabled else None,
            judge=PreferenceJudge(self._session) if self._policy.tournament else None,
            subjects=(
                SubjectBakeOff(self._session) if self._policy.subject_variants else None
            ),
            subject_variants=self._policy.subject_variants,
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
            positioning=positioning,
            observer=self._observer,
            cancel_token=self._cancel_token,
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

    def _needs_input(
        self,
        request: CampaignRequest,
        contract: DeliverableContract,
        result: CampaignRunResult,
        posture: "ProofPosture",
    ) -> CampaignRunResult:
        """Stop before the strategy, and say what would unblock it.

        This is the one refusal in the pipeline, and it exists because the
        alternative is not a worse campaign - it is the same campaign, written,
        disbelieved by a cold reader, rewritten and disbelieved again. No
        rewrite has ever added a proof the material did not contain, so a run
        with nothing to argue from spends its whole budget discovering
        something `preflight.assess` establishes for free before the first
        model call.

        Narrow on purpose. It fires only when there is neither third-party
        proof *nor* anything a reader could check for themselves - the case
        where every sentence would be this company asserting something about
        itself - or when the compiler found a hole a campaign cannot be written
        around at all, like no action to ask for. A business with no
        testimonials but a real price, a real limit and a real mechanism is not
        blocked: specific beats persuasive, and that campaign is worth writing.
        """
        result.status = "needs_input"
        result.abort_reason = (
            "Nothing here can carry a campaign yet: "
            + posture.summary().lower()
            + ". Answering the questions below is worth more than any rewrite."
        )
        result.report = self._build_report(request, contract, result)
        result.report.questions = list(posture.asks)
        self._observer.on_report(result.report)
        self._observer.on_phase(
            "stopped",
            result.abort_reason,
            {"status": "needs_input", "questions": posture.asks},
        )
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
                evidence_assigned=outcome.brief.evidence_ids,
                evidence_spent=list(outcome.best.substantiation.carried),
                attributions=outcome.best.substantiation.attributions,
                unresolved=[issue.detail for issue in outcome.best.gates.blocking],
                reader_verdicts=ReaderVerdict.from_panel(outcome.best.read),
                sameness=[
                    issue.detail
                    for issue in outcome.best.gates.issues
                    if issue.gate == "sameness"
                ],
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
            notes=(
                ([result.abort_reason] if result.abort_reason else [])
                + self._economy_note(lines)
            ),
        )

    def _economy_note(self, lines: list[EmailReportLine]) -> list[str]:
        """Say when the copy scored badly because of what the run was allowed
        to buy, rather than because of the material.

        A preset is presented as a speed choice and is really a quality one:
        the cheapest configuration writes one draft instead of several,
        reads it with one stranger instead of three, skips the critic, skips
        the subject bake-off and allows one rewrite. Every mechanism this
        system's quality rests on is off.

        A user who picked it and got a 4/10 has no way to know that, and the
        number they are shown looks like a verdict on their product. It is a
        verdict on a run that was not allowed to do any of the work. Naming it
        is free and it is the difference between "this tool is not very good"
        and "spend forty cents more".
        """
        below = [line for line in lines if line.read_reported and not line.landed]
        if not below:
            return []
        starved = [
            name
            for name, on in (
                ("more than one opening per email", self._policy.draft_candidates > 1),
                ("a panel of cold readers rather than one", self._policy.reader_panel),
                ("the conversion critic", self._policy.critic_enabled),
                ("alternative subject lines", self._policy.subject_variants > 0),
                ("more than one rewrite", self._policy.max_revisions > 1),
            )
            if not on
        ]
        if len(starved) < 3:
            return []
        return [
            f"{len(below)} email(s) came in under the floor on a run configured without "
            + ", ".join(starved)
            + ". Those are the mechanisms the quality rests on - this run wrote one draft "
            "and kept it. Before concluding the copy cannot be better, try the same "
            "request on a preset that buys them."
        ]
