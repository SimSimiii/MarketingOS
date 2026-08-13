"""The craft loop: how a draft becomes an email that would actually get clicked.

Draft, check it mechanically, have it read by someone who knows nothing, have
that reading converted into edits by someone who knows everything, rewrite,
keep the better version. This protocol was the best thing in the old codebase
and it was a private method of one specialist; here it is the centre of the
system.

Two rules hold it together. Only the deterministic gates can block - taste
never blocks, or a run spends its budget arguing with a model about a
sentence. And a rewrite is kept only if it actually came back better, because
rewriting copy that already worked usually sands the edges off it.

The loop starts wide and then narrows. Several openings are drafted, screened
by the free checks and one cold read, and only the one a stranger actually
responded to earns the critic and the rewrites. Refinement alone cannot do
this job: it walks a single draft toward the middle of the register it started
in, answering each reader's last objection by removing whatever made the copy
specific. Which argument a cold reader responds to is not derivable from the
brief, and the cheapest way to find out is to write more than one and ask.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from functools import reduce

from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.ledger import EvidenceIndex
from app.marketing.briefs import CampaignBrief, EmailBrief
from app.marketing.critic import ConversionCritic, Critique
from app.marketing.email_copy import Email
from app.marketing.gates import GateReport, run_all
from app.marketing.observer import RunObserver
from app.marketing.reader import BlindReader, PanelRead
from app.marketing.request import CampaignRequest
from app.marketing.writer import EmailWriter

logger = logging.getLogger("marketingos.marketing")

#: Where a first draft is allowed to start. These are different arguments for
#: the same product rather than one argument phrased four ways - an email that
#: opens on the reader's Tuesday and an email that opens on a number are not
#: variants, they are competing bets about what earns the second line. Order
#: matters: a run configured for two candidates gets the first two, which are
#: the two that least resemble each other.
_OPENING_MOVES: tuple[str, ...] = (
    (
        "Open on the reader's own situation, in the words they would use for it themselves - "
        "the specific Tuesday this lands on. No product, no company, no claim in the first "
        "two sentences."
    ),
    (
        "Open on the single most concrete thing in the evidence you were given - a number, a "
        "mechanism, a named limit - and let the reader work out what it means for them before "
        "you explain it."
    ),
    (
        "Open on the objection this email has to beat, stated more plainly and more bluntly "
        "than the reader would put it themselves, then spend the email earning the right to "
        "answer it."
    ),
    (
        "Open on what it costs them to change nothing, in terms they can check against their "
        "own week. Not fear, not urgency you invented - the arithmetic they have not done."
    ),
)


def _history(versions: list["EmailVersion"]) -> str:
    """Every attempt already made on this email, and how each one read.

    The rewrite loop had no memory: each turn saw the current draft and the
    last reader's report, and nothing about the attempts before it. So the
    third rewrite was free to walk back onto the angle the first one was
    thrown away for - at full price, with a fresh cold read and a fresh
    critique, and nothing in the record to show it had happened before.

    Deliberately the subject, the score and the doubt rather than the whole
    draft: the writer needs to know which ground has already been tried and
    what it cost, and four rendered emails in a prompt is how a rewrite starts
    averaging them together instead of replacing them.
    """
    if not versions:
        return ""
    lines: list[str] = []
    for version in versions:
        read = version.read
        verdict = f"pull {read.pull:.0f}/10" if read.has_verdict else "nobody could read it"
        doubt = read.worst.biggest_doubt.strip()
        lines.append(
            f'- Attempt {version.attempt}, "{version.email.subject}" - {verdict}'
            + (f"; what stopped them: {doubt}" if doubt else "")
        )
    return (
        "What has already been tried on this email:\n"
        + "\n".join(lines)
        + "\n\nThose are the versions that did not work. Do not return to a subject line or an "
        "opening move that has already been read here - it has been measured, and it did not "
        "land. If the ground you were about to take is on that list, take different ground."
    )


@dataclass
class EmailVersion:
    """One attempt at one email, with everything that judged it."""

    attempt: int
    email: Email
    gates: GateReport
    read: PanelRead
    critique: Critique | None = None
    #: True when this run has a critic but deliberately did not spend it on
    #: this version - the final attempt, whose edits nothing could consume.
    #: Distinct from a run with no critic at all: there, no version was
    #: judged and they compare on equal terms; here, one version was not.
    critic_skipped: bool = False

    @property
    def ships(self) -> bool:
        # A read that never came back is no verdict rather than a bad one, and
        # the draft stands on the checks that did report. It is not allowed to
        # count as a good verdict - see BlindRead.reported.
        return (
            self.gates.passed
            and (self.read.landed or not self.read.has_verdict)
            and (self.critique is None or self.critique.verdict == "ship")
        )

    @property
    def approved(self) -> bool:
        """Whether the critic would let this go. Vacuously true when nobody
        asked - `critic_judged` is what says whether that means anything."""
        return self.critique is None or self.critique.verdict == "ship"

    @property
    def critic_judged(self) -> bool:
        return self.critique is not None

    @property
    def score(self) -> tuple[int, int, float]:
        """How to choose between two versions of the same email.

        Ordered by what a user would actually care about: an email with an
        unsupported claim or a broken structure is not in the running however
        well it reads, then the critic's verdict, then how much the cold
        reader wanted the thing.

        Only valid between two versions the critic treated alike - see
        `better_of`, which is what `EmailOutcome.best` actually uses.
        """
        return (
            0 if self.gates.blocking else 1,
            1 if self.approved else 0,
            self.read.pull,
        )

    def describe(self) -> str:
        parts = [
            f"pull {self.read.pull:.0f}/10" if self.read.has_verdict else "nobody could read it"
        ]
        if self.gates.blocking:
            parts.append(f"{len(self.gates.blocking)} automatic check(s) failed")
        if self.critique is not None:
            parts.append(f"critic says {self.critique.verdict}")
        return ", ".join(parts)


def better_of(left: EmailVersion, right: EmailVersion) -> EmailVersion:
    """Which of two versions of the same email is the one to keep.

    Gates first - an email making an unsupported claim is not in the running
    however well it reads. Then the critic's verdict, but *only when it judged
    both*: the final attempt deliberately goes uncritiqued, and scoring an
    unasked version as approved would hand it a point it never earned, letting
    a draft nobody vetted beat one the critic had explicitly sent back. Then
    how much the cold reader wanted the thing, which is the question the whole
    loop exists to move.

    Ties go to the earlier version: if a rewrite did not measurably improve
    anything, the draft that already worked stands.
    """
    if bool(left.gates.blocking) is not bool(right.gates.blocking):
        return right if left.gates.blocking else left
    if left.critic_judged and right.critic_judged and left.approved is not right.approved:
        return left if left.approved else right
    if left.read.pull != right.read.pull:
        return left if left.read.pull > right.read.pull else right
    return left if left.attempt <= right.attempt else right


@dataclass
class EmailOutcome:
    """Everything that happened to one email, and which version won."""

    brief: EmailBrief
    versions: list[EmailVersion] = field(default_factory=list)
    #: True when the loop stopped because rewriting had stopped improving the
    #: draft, rather than because it ran out of attempts. The two look
    #: identical on a receipt and are not the same thing: one is a judgment,
    #: the other is a budget.
    stopped_early: bool = False

    @property
    def best(self) -> EmailVersion:
        return reduce(better_of, self.versions)

    @property
    def email(self) -> Email:
        return self.best.email

    @property
    def shipped_clean(self) -> bool:
        return self.best.ships


class CraftLoop:
    """Turns one Email Brief into one finished email."""

    def __init__(
        self,
        *,
        writer: EmailWriter,
        reader: BlindReader,
        critic: ConversionCritic | None,
        artifacts: KnowledgeArtifacts,
        evidence: EvidenceIndex,
        personas: list[str],
        merge_fields: list[str],
        max_revisions: int = 2,
        candidates: int = 1,
        observer: RunObserver | None = None,
    ) -> None:
        self._writer = writer
        self._reader = reader
        self._critic = critic
        self._artifacts = artifacts
        self._evidence = evidence
        self._personas = personas
        self._merge_fields = merge_fields
        self._max_revisions = max_revisions
        self._candidates = max(1, min(candidates, len(_OPENING_MOVES)))
        self._observer = observer or RunObserver()

    async def craft(
        self,
        *,
        brief: EmailBrief,
        campaign: CampaignBrief,
        request: CampaignRequest,
        previous: list[Email],
    ) -> EmailOutcome:
        outcome = EmailOutcome(brief=brief)

        # The bake-off has already paid for the winner's gates and cold read;
        # `screened` carries them into the first judgment so the loop does not
        # buy the same reading twice.
        draft, screened = await self._first_draft(brief, campaign, request, previous)

        for attempt in range(1, self._max_revisions + 2):
            best_before = outcome.best if outcome.versions else None
            version = await self._judge(
                draft,
                brief,
                campaign,
                previous,
                attempt,
                screened=screened,
                # On the last permitted attempt the loop breaks regardless of
                # what the critic says, so its edits have no consumer - it is
                # a deep-tier call bought after the outcome is already decided.
                #
                # Unless it is also the first attempt: a run configured for no
                # rewrites at all would otherwise never critique anything, and
                # the critique is not only an instruction to the writer. Its
                # brief drift and unspent evidence are what the user is shown
                # about why an email is the way it is, and an email with no
                # judgment on the record at all is a worse deliverable than a
                # critique nobody could act on.
                final=attempt > self._max_revisions and attempt > 1,
            )
            screened = None
            outcome.versions.append(version)

            if version.ships or attempt > self._max_revisions:
                break

            # A rewrite that came back no better than what it replaced is the
            # signal that more rewriting is not what this draft needs. Spending
            # the rest of the budget anyway buys a third and fourth attempt at
            # the same score - and, with nothing carrying forward but the last
            # reader's report, it can walk straight back onto an angle that was
            # already read and thrown away. The best version is kept either
            # way; what stops is paying to look for a better one.
            if best_before is not None and version.score <= best_before.score:
                outcome.stopped_early = True
                logger.info(
                    "craft: email %d rewrite %d did not improve on attempt %d - stopping",
                    brief.position,
                    attempt - 1,
                    best_before.attempt,
                )
                self._observer.on_phase(
                    "craft",
                    f"Email {brief.position}: rewrite {attempt - 1} did not read better than "
                    f"the version before it - stopping rather than spending "
                    f"{self._max_revisions - attempt + 1} more rewrite(s) on it",
                    {
                        "position": brief.position,
                        "attempt": attempt,
                        "rewrites_left": self._max_revisions - attempt + 1,
                    },
                )
                break

            logger.info(
                "craft: email %d attempt %d did not land (%s) - revising",
                brief.position,
                attempt,
                version.describe(),
            )
            draft = await self._revise(
                version, brief, campaign, request, previous, attempt + 1,
                critique_notes=version.critique.render() if version.critique else "",
                history=_history(outcome.versions),
            )

        self._observer.on_email_accepted(brief.position, outcome.best)
        return outcome

    async def rework(
        self,
        *,
        outcome: EmailOutcome,
        campaign: CampaignBrief,
        request: CampaignRequest,
        previous: list[Email],
        instruction: str,
    ) -> EmailOutcome:
        """One extra pass driven by something outside this email - the
        sequence pass finding that it repeats email 2's opening move, say."""
        best = outcome.best
        attempt = len(outcome.versions) + 1
        draft = await self._revise(
            best,
            outcome.brief,
            campaign,
            request,
            previous,
            attempt,
            critique_notes=instruction,
            history=_history(outcome.versions),
        )
        version = await self._judge(draft, outcome.brief, campaign, previous, attempt)
        outcome.versions.append(version)
        self._observer.on_email_accepted(outcome.brief.position, outcome.best)
        return outcome

    # ------------------------------------------------------------- internals

    async def _first_draft(
        self,
        brief: EmailBrief,
        campaign: CampaignBrief,
        request: CampaignRequest,
        previous: list[Email],
    ) -> tuple[Email, tuple[GateReport, PanelRead] | None]:
        if self._candidates <= 1:
            return await self._draft(brief, campaign, request, previous), None
        return await self._bake_off(brief, campaign, request, previous)

    async def _draft(
        self,
        brief: EmailBrief,
        campaign: CampaignBrief,
        request: CampaignRequest,
        previous: list[Email],
    ) -> Email:
        self._observer.on_role_started(
            "email_writer",
            f"Email {brief.position} · first draft",
            {"position": brief.position, "attempt": 1},
        )
        draft = await self._writer.draft(
            brief=brief,
            campaign=campaign,
            request=request,
            artifacts=self._artifacts,
            previous=previous,
        )
        self._observer.on_draft(brief.position, 1, draft)
        self._observer.on_role_finished(
            "email_writer", f'Drafted "{draft.subject}"', {"subject": draft.subject}
        )
        return draft

    async def _bake_off(
        self,
        brief: EmailBrief,
        campaign: CampaignBrief,
        request: CampaignRequest,
        previous: list[Email],
    ) -> tuple[Email, tuple[GateReport, PanelRead]]:
        """Several openings written, one kept.

        Only the free checks and the cold read decide the winner. The critic
        and every rewrite are spent afterwards on the survivor, where they
        compound, instead of being split across drafts that are about to be
        thrown away - three half-refined candidates are worse than one refined
        one, and cost the same.

        The candidates are drafted concurrently but announced as a single
        role turn: they are one decision, they are billed together, and the
        observer's step bookkeeping pairs one start with one finish.
        """
        moves = _OPENING_MOVES[: self._candidates]
        self._observer.on_role_started(
            "email_writer",
            f"Email {brief.position} · {len(moves)} openings, first draft",
            {"position": brief.position, "attempt": 1, "candidates": len(moves)},
        )
        written = await asyncio.gather(
            *(
                self._writer.draft(
                    brief=brief,
                    campaign=campaign,
                    request=request,
                    artifacts=self._artifacts,
                    previous=previous,
                    opening_move=move,
                )
                for move in moves
            ),
            return_exceptions=True,
        )
        drafts = [item for item in written if isinstance(item, Email)]
        if not drafts:
            # Every opening failed, which makes it the format and not the
            # angle. Surface the first failure rather than a summary of four.
            raise next(item for item in written if isinstance(item, BaseException))
        for failure in (item for item in written if isinstance(item, BaseException)):
            logger.info("craft: one opening for email %d failed - %s", brief.position, failure)
        for draft in drafts:
            self._observer.on_draft(brief.position, 1, draft)
        self._observer.on_role_finished(
            "email_writer",
            f"{len(drafts)} opening(s): " + "; ".join(f'"{draft.subject}"' for draft in drafts),
            {"subjects": [draft.subject for draft in drafts]},
        )

        gates = [
            run_all(
                draft,
                evidence=self._evidence,
                offer=self._artifacts.offer,
                previous=previous,
                merge_fields=self._merge_fields,
            )
            for draft in drafts
        ]
        self._observer.on_role_started(
            "blind_reader",
            f"Email {brief.position} · {len(drafts)} opening(s) read cold by "
            f"{len(self._personas)} reader(s)",
            {"position": brief.position, "attempt": 1, "candidates": len(drafts)},
        )
        reads = await asyncio.gather(
            *(self._reader.read(draft, self._personas) for draft in drafts)
        )
        winner, winning_gates, winning_read = max(
            zip(drafts, gates, reads, strict=True),
            key=lambda item: (0 if item[1].blocking else 1, item[2].pull),
        )
        self._observer.on_role_finished(
            "blind_reader",
            "Openings scored "
            + ", ".join(f"{read.pull:.0f}/10" for read in reads)
            + f' - kept "{winner.subject}"',
            {"pull": winning_read.pull, "scores": [read.pull for read in reads]},
        )
        # Announced for the winner only: these are the readings the rest of
        # the loop actually works from, and the timeline is a record of what
        # happened to the email that shipped.
        self._observer.on_gates(brief.position, 1, winning_gates)
        self._observer.on_read(brief.position, 1, winning_read)
        return winner, (winning_gates, winning_read)

    async def _revise(
        self,
        version: EmailVersion,
        brief: EmailBrief,
        campaign: CampaignBrief,
        request: CampaignRequest,
        previous: list[Email],
        attempt: int,
        critique_notes: str,
        history: str = "",
    ) -> Email:
        self._observer.on_role_started(
            "email_writer",
            f"Email {brief.position} · rewrite {attempt - 1}",
            {"position": brief.position, "attempt": attempt},
        )
        draft = await self._writer.revise(
            draft=version.email,
            brief=brief,
            campaign=campaign,
            request=request,
            artifacts=self._artifacts,
            previous=previous,
            gates=version.gates,
            read=version.read,
            critique_notes=critique_notes,
            history=history,
        )
        self._observer.on_draft(brief.position, attempt, draft)
        self._observer.on_role_finished(
            "email_writer", f'Rewrote as "{draft.subject}"', {"subject": draft.subject}
        )
        return draft

    async def _judge(
        self,
        draft: Email,
        brief: EmailBrief,
        campaign: CampaignBrief,
        previous: list[Email],
        attempt: int,
        screened: tuple[GateReport, PanelRead] | None = None,
        final: bool = False,
    ) -> EmailVersion:
        """Free checks first, then the cold reader, then the critic.

        The order is a cost decision as much as a quality one: the gates cost
        nothing and catch the failures that would make every later opinion
        moot, so they run before anything is paid for. `screened` is that same
        pair already bought during the bake-off, for the one draft that won it.

        `final` marks the attempt after which no rewrite can happen. The
        critic is skipped there: it is the most expensive judge in the loop and
        its entire output is a list of edits for a rewrite that will not be
        bought. Its verdict does feed `EmailVersion.score`, but only as a
        tie-break between versions the gates and the cold reader already rank -
        and the version chosen on this attempt is chosen the same way with the
        critique absent, which `ships` and `score` both already handle.
        """
        if screened is not None:
            gates, read = screened
        else:
            gates = run_all(
                draft,
                evidence=self._evidence,
                offer=self._artifacts.offer,
                previous=previous,
                merge_fields=self._merge_fields,
            )
            self._observer.on_gates(brief.position, attempt, gates)

            self._observer.on_role_started(
                "blind_reader",
                f"Email {brief.position} · read cold by {len(self._personas)} reader(s)",
                {"position": brief.position, "attempt": attempt},
            )
            read = await self._reader.read(draft, self._personas)
            self._observer.on_read(brief.position, attempt, read)
            self._observer.on_role_finished(
                "blind_reader",
                f"Pull {read.pull:.0f}/10 - {read.verdict_line()}",
                {"pull": read.pull},
            )

        critique: Critique | None = None
        if self._critic is not None and not final:
            self._observer.on_role_started(
                "conversion_critic",
                f"Email {brief.position} · conversion critique",
                {"position": brief.position, "attempt": attempt},
            )
            critique = await self._critic.critique(
                email=draft,
                brief=brief,
                campaign=campaign,
                artifacts=self._artifacts,
                read=read,
                gates=gates,
            )
            self._observer.on_critique(brief.position, attempt, critique)
            self._observer.on_role_finished(
                "conversion_critic",
                f"{critique.verdict} - {len(critique.edits)} edit(s) requested",
                {"verdict": critique.verdict},
            )

        return EmailVersion(
            attempt=attempt,
            email=draft,
            gates=gates,
            read=read,
            critique=critique,
            critic_skipped=self._critic is not None and final,
        )
