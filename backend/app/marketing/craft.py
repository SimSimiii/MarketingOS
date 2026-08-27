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

The loop starts wide and then narrows. Several candidates are drafted, screened
by the free checks and one cold read, and only the one a stranger actually
responded to earns the critic and the rewrites. Refinement alone cannot do
this job: it walks a single draft toward the middle of the register it started
in, answering each reader's last objection by removing whatever made the copy
specific. Which argument a cold reader responds to is not derivable from the
brief, and the cheapest way to find out is to write more than one and ask.

Three things about *how* it narrows were rebuilt after a measured run in which
every one of them failed silently.

**The candidates are different arguments, not different first sentences.** The
bake-off used to vary only where a draft opened, on a claim the strategist had
already fixed, so three drafts were three ways into one bet - and in that run
two of the three came back with the same subject line. Now each candidate
argues a different claim from `EmailBrief.alternative_ideas` where the brief
supplies them, and near-identical drafts are dropped before anybody pays to
read them.

**Better is a comparison, not a score.** Which of two versions to keep used to
be decided by comparing two absolute 0-10 ratings from a cold reader. Those
ratings saturate - see reader.py - so a rewrite that changed nothing and a
rewrite that changed everything both came back level with what they replaced,
and the loop read the tie as "rewriting has stopped helping". Now the two
drafts are put in front of the reader together and the reader picks one.

**A stalled email gets a different argument, not another rewrite.** When the
copy stops moving, the thing that is not working is usually the claim, and no
rewrite is allowed to change the claim. So the loop pivots to an untried
alternative once, from scratch, instead of buying a fourth phrasing of a bet
that has already been measured twice.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from functools import reduce

from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.ledger import EvidenceIndex
from app.market.positioning import PositioningMap
from app.marketing.briefs import CampaignBrief, EmailBrief
from app.marketing.cancellation import CancellationToken
from app.marketing.critic import ConversionCritic, Critique
from app.marketing.email_copy import Email, normalized
from app.marketing.gates import GateReport, run_all
from app.marketing.observer import RunObserver
from app.marketing.reader import BlindReader, PanelRead
from app.marketing.request import CampaignRequest
from app.marketing.subject_lines import SubjectBakeOff
from app.marketing.substantiation import Substantiation
from app.marketing.tournament import Duel, PreferenceJudge
from app.marketing.writer import EmailWriter

logger = logging.getLogger("marketingos.marketing")

#: Where a first draft is allowed to start. These are different arguments for
#: the same product rather than one argument phrased four ways - an email that
#: opens on the reader's Tuesday and an email that opens on a number are not
#: variants, they are competing bets about what earns the second line. Order
#: matters: a run configured for two candidates gets the first two, which are
#: the two that least resemble each other.
#:
#: Since the brief carries alternative claims, these do the second job rather
#: than the whole one: candidate n argues alternative claim n and opens on move
#: n, and where the brief named no alternatives the opening move is all the
#: variety there is - which is the behaviour this list was written for.
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

#: How many words of the opening two drafts have to share before they count as
#: the same draft. Long enough that the match is a shared move rather than a
#: shared idiom, short enough to catch the failure it exists for: in a measured
#: run two of three candidates came back with the same subject and the same
#: first sentence, and both were read cold at full price.
_SAME_OPENING_WORDS = 8


def _opening_line(email: Email) -> str:
    """The sentence the reader decides on. Everything else in the email is
    read only if this one earns it, so it is the part of a failed attempt the
    next one most needs to see."""
    return next((line.strip() for line in email.body.splitlines() if line.strip()), "")


def _attempt_line(version: "EmailVersion", label: str) -> str:
    read = version.read
    if read.has_verdict:
        verdict = f"pull {read.pull:.0f}/10"
    elif version.gates.blocking:
        # A candidate the free checks vetoed is never read cold - see
        # `_bake_off`. "Nobody could read it" would report that as a reader who
        # failed to answer, which is a different thing and the wrong lesson:
        # the writer needs the check it broke, not a missing score.
        verdict = f"stopped by an automatic check - {version.gates.blocking[0].detail}"
    else:
        verdict = "nobody could read it"
    doubt = read.worst.biggest_doubt.strip()
    wanted = read.worst.to_click_it_would_have_to.strip()
    opening = _opening_line(version.email)
    return (
        f'- {label}, "{version.email.subject}"'
        + (f' - opened on "{opening}"' if opening else "")
        + f" - {verdict}"
        + (f"; what stopped them: {doubt}" if doubt else "")
        + (f"; what they said would have worked: {wanted}" if wanted else "")
    )


def _history(
    versions: list["EmailVersion"], discarded: list["EmailVersion"] | None = None
) -> str:
    """Every attempt already made on this email, and how each one read.

    The rewrite loop had no memory: each turn saw the current draft and the
    last reader's report, and nothing about the attempts before it. So the
    third rewrite was free to walk back onto the angle the first one was
    thrown away for - at full price, with a fresh cold read and a fresh
    critique, and nothing in the record to show it had happened before.

    Deliberately the subject, the opening line, the score and the doubt rather
    than the whole draft: the writer needs to know which ground has already
    been tried and what it cost, and four rendered emails in a prompt is how a
    rewrite starts averaging them together instead of replacing them.

    The opening line is here because a subject alone did not identify the
    ground. In a measured run the second rewrite came back with a new subject
    over the same first sentence a cold panel had already scored 2/10 twice -
    the subject had changed, so nothing in the history said it was the same
    bet, and the loop paid for a third reading of an argument it had already
    measured.

    `discarded` are the openings the bake-off wrote and did not keep. They
    were drafted, gated and read cold like everything else, and were then
    invisible to every rewrite that followed - which is how a rewrite ends up
    re-proposing the candidate that lost the bake-off.
    """
    lines = [
        _attempt_line(version, "An opening drafted first and not taken forward")
        for version in (discarded or [])
    ] + [_attempt_line(version, f"Attempt {version.attempt}") for version in versions]
    if not lines:
        return ""
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
    #: What of the material behind this email reached the page - the assigned
    #: facts it actually spent, whether it names anyone, how many checkable
    #: specifics it carries. Computed in code, for free, alongside the gates.
    #: It is here rather than in the gate report because two of its counts
    #: decide which version ships; see `measured` and `better_of`.
    substantiation: Substantiation = field(default_factory=Substantiation)
    critique: Critique | None = None
    #: True when this run has a critic but deliberately did not spend it on
    #: this version - the final attempt, whose edits nothing could consume.
    #: Distinct from a run with no critic at all: there, no version was
    #: judged and they compare on equal terms; here, one version was not.
    critic_skipped: bool = False
    #: How this version did against the one it was trying to replace, when a
    #: preference judge was asked. Kept on the version rather than thrown away
    #: with the decision, because "3-1, they said the new one told them what it
    #: costs" is the only readable account of why an email is the one that
    #: shipped.
    duel: Duel | None = None
    #: The claim this draft argued, when it is not the brief's own. Set on
    #: bake-off candidates and on a pivot.
    idea: str = ""

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
    def measured(self) -> tuple[int, float, int, int]:
        """What the free checks and the cold reader made of this version.

        Separate from `score` because it is the half of the judgment that does
        not need the critic, and the loop has to know whether a rewrite moved
        the copy *before* it decides whether to buy a critique of it. Whether
        the critic likes a draft is also not what "did this rewrite help" is
        asking.

        Substantiation comes *after* pull and never before it. It is a
        tiebreak, and only a tiebreak: how much a stranger wanted the thing is
        the question the loop exists to move, and a rule that put proof above
        it would ship a well-cited email nobody would open. Where it earns its
        place is the case the bake-off's own docstring names - candidates that
        come back 5, 5 and 4, where the scores have said which one to throw
        away and nothing at all about the other two. Between two drafts a
        cold reader could not separate, the one that put the evidence on the
        page is the better email, and that is not a matter of opinion.
        """
        return (
            0 if self.gates.blocking else 1,
            self.read.pull,
            len(self.substantiation.carried),
            self.substantiation.attributions,
        )

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

    This is the fallback. When a preference judge is available the loop decides
    with a duel instead and records the winner on the outcome - see
    `EmailOutcome.best`. Two saturated scores cannot be compared, and this
    function is a comparison of two scores.
    """
    if bool(left.gates.blocking) is not bool(right.gates.blocking):
        return right if left.gates.blocking else left
    if left.critic_judged and right.critic_judged and left.approved is not right.approved:
        return left if left.approved else right
    if left.read.pull != right.read.pull:
        return left if left.read.pull > right.read.pull else right
    # Two versions a cold reader could not separate. The one still standing on
    # the material is the one to keep - and without this the tie went to
    # whichever was written first, which is how a rewrite that quietly dropped
    # the proof paragraph inherited the title.
    if left.substantiation.weaker_than(right.substantiation):
        return right
    if right.substantiation.weaker_than(left.substantiation):
        return left
    return left if left.attempt <= right.attempt else right


@dataclass
class EmailOutcome:
    """Everything that happened to one email, and which version won."""

    brief: EmailBrief
    versions: list[EmailVersion] = field(default_factory=list)
    #: The bake-off's losing candidates. Kept out of `versions` because they
    #: are not attempts at the email that shipped and must not compete with it
    #: in `best` - they lost that comparison once already, at the same attempt
    #: number, where a tie would have gone to whichever was drafted first.
    #: Kept at all because they were read cold, and a rewrite that cannot see
    #: them can spend an attempt re-proposing one.
    discarded: list[EmailVersion] = field(default_factory=list)
    #: True when the loop stopped because rewriting had stopped improving the
    #: draft, rather than because it ran out of attempts. The two look
    #: identical on a receipt and are not the same thing: one is a judgment,
    #: the other is a budget.
    stopped_early: bool = False
    #: The attempt the reader preferred, when duels decided it. Recorded rather
    #: than recomputed: a duel is a measurement, and `best` recomputing a
    #: winner from scores would quietly overrule it with the number the duels
    #: exist to replace.
    champion_attempt: int = 0
    #: The claim the loop moved to when the first one stopped working, if it
    #: did. At most one per email.
    pivoted_to: str = ""

    @property
    def best(self) -> EmailVersion:
        if self.champion_attempt:
            champion = next(
                (item for item in self.versions if item.attempt == self.champion_attempt), None
            )
            if champion is not None:
                return champion
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
        judge: PreferenceJudge | None = None,
        subjects: SubjectBakeOff | None = None,
        subject_variants: int = 0,
        positioning: PositioningMap | None = None,
        observer: RunObserver | None = None,
        cancel_token: CancellationToken | None = None,
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
        self._judge = judge
        self._subjects = subjects
        self._subject_variants = subject_variants
        #: Where this company stands against the field. Only the free
        #: checks read it - see `gates.sameness_gate`. None means nobody
        #: has scanned this market, and the check degrades to its closed
        #: list of interchangeable openings rather than passing everything.
        self._positioning = positioning
        self._observer = observer or RunObserver()
        #: Checked between an attempt's cold read and the next round of paid
        #: calls (critique, revise) - the pipeline's own guard only checks
        #: between whole emails, and one email can be a bake-off plus several
        #: revisions, each a deep-tier call. Without this, "Stop" could sit
        #: behind most of an email's remaining budget before it took effect.
        self._cancel_token = cancel_token

    def _cancelled(self) -> bool:
        return self._cancel_token is not None and self._cancel_token.is_cancelled

    def _check(
        self, draft: Email, brief: EmailBrief, previous: list[Email]
    ) -> tuple[GateReport, Substantiation]:
        """Every free check on one draft, in one place.

        The argument list was copied out at three call sites and it is now
        long enough that a fourth would have drifted - the bake-off, the
        per-attempt judgment and the subject swap must all check the same
        things, or the loop keeps a draft that was never checked the way its
        rivals were.
        """
        return run_all(
            draft,
            evidence=self._evidence,
            offer=self._artifacts.offer,
            previous=previous,
            merge_fields=self._merge_fields,
            assigned=[
                entry
                for id_ in brief.evidence_ids
                if (entry := self._artifacts.evidence.get(id_)) is not None
            ],
            ledger=self._artifacts.evidence.entries,
            positioning=self._positioning,
        )

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
        draft, screened, discarded, idea = await self._first_draft(
            brief, campaign, request, previous
        )
        outcome.discarded = discarded

        for attempt in range(1, self._max_revisions + 2):
            champion = outcome.best if outcome.versions else None
            version = await self._judge_draft(
                draft, brief, attempt, previous, screened=screened, idea=idea
            )
            screened = None
            outcome.versions.append(version)

            # Whether this attempt is the one to keep, settled before anything
            # else is bought. A duel where there is a judge, the free checks
            # and the cold reader where there is not.
            improved = champion is None or await self._prefers(version, champion, brief)
            if improved:
                outcome.champion_attempt = version.attempt

            last_attempt = attempt > self._max_revisions
            stalled = champion is not None and not improved

            if last_attempt or stalled:
                # No rewrite is going to be bought, so the critic has no
                # consumer: its entire output is a list of edits for a pass
                # that will not happen. This is the ordering that matters -
                # the old loop critiqued first and discovered afterwards that
                # the rewrite had stalled, which in a measured run bought a
                # deep-tier call, 49 seconds and 13% of the run for nothing.
                if stalled and (pivot := self._pivot_idea(outcome)) and not last_attempt:
                    outcome.pivoted_to = pivot
                    self._observer.on_phase(
                        "craft",
                        f"Email {brief.position}: rewriting stopped moving this argument - "
                        f"trying a different one instead ({pivot})",
                        {"position": brief.position, "attempt": attempt, "pivot": pivot},
                    )
                    draft, idea = await self._pivot_draft(
                        outcome, brief, campaign, request, previous, attempt + 1, pivot
                    )
                    continue
                if stalled:
                    outcome.stopped_early = True
                    self._announce_stall(brief, attempt)
                break

            if self._cancelled():
                # A stop was requested while this attempt's cold read was in
                # flight. That call already happened and is kept - breaking
                # here only skips the critique and revise this attempt would
                # otherwise have bought.
                break

            version.critique = await self._critique(version, brief, campaign, attempt)
            if version.ships:
                break

            logger.info(
                "craft: email %d attempt %d did not land (%s) - revising",
                brief.position,
                attempt,
                version.describe(),
            )
            idea = version.idea
            draft = await self._revise(
                version, brief, campaign, request, previous, attempt + 1,
                critique_notes=version.critique.render() if version.critique else "",
                history=_history(outcome.versions, outcome.discarded),
            )

        if not self._cancelled():
            await self._critique_for_the_record(outcome, brief, campaign)
            await self._polish_subject(outcome, brief, previous)
        if self._critic is not None:
            # Which versions the critic was never asked about, recorded rather
            # than inferred. `better_of` needs to know that an uncritiqued
            # version is unjudged and not approved, and a receipt that shows a
            # draft as unopposed when nobody opposed it is a lie of omission.
            for version in outcome.versions:
                version.critic_skipped = version.critique is None
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
        champion = outcome.best
        attempt = len(outcome.versions) + 1
        draft = await self._revise(
            champion,
            outcome.brief,
            campaign,
            request,
            previous,
            attempt,
            critique_notes=instruction,
            history=_history(outcome.versions, outcome.discarded),
        )
        version = await self._judge_draft(
            draft, outcome.brief, attempt, previous, idea=champion.idea
        )
        outcome.versions.append(version)
        if await self._prefers(version, champion, outcome.brief):
            outcome.champion_attempt = version.attempt
        self._observer.on_email_accepted(outcome.brief.position, outcome.best)
        return outcome

    # ------------------------------------------------------------- internals

    async def _first_draft(
        self,
        brief: EmailBrief,
        campaign: CampaignBrief,
        request: CampaignRequest,
        previous: list[Email],
    ) -> tuple[
        Email,
        tuple[GateReport, Substantiation, PanelRead] | None,
        list[EmailVersion],
        str,
    ]:
        if self._candidates <= 1:
            draft = await self._draft(brief, campaign, request, previous)
            return draft, None, [], brief.single_idea
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
    ) -> tuple[Email, tuple[GateReport, Substantiation, PanelRead], list[EmailVersion], str]:
        """Several arguments written, one kept.

        Only the free checks and the cold read decide the winner. The critic
        and every rewrite are spent afterwards on the survivor, where they
        compound, instead of being split across drafts that are about to be
        thrown away - three half-refined candidates are worse than one refined
        one, and cost the same.

        The candidates are drafted concurrently but announced as a single
        role turn: they are one decision, they are billed together, and the
        observer's step bookkeeping pairs one start with one finish.
        """
        bets = _bets(brief, self._candidates)
        self._observer.on_role_started(
            "email_writer",
            f"Email {brief.position} · {len(bets)} candidate(s), first draft",
            {
                "position": brief.position,
                "attempt": 1,
                "candidates": len(bets),
                "ideas": [idea for idea, _ in bets],
            },
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
                    idea_override="" if idea == brief.single_idea else idea,
                )
                for idea, move in bets
            ),
            return_exceptions=True,
        )
        drafted = [
            (bets[index][0], item)
            for index, item in enumerate(written)
            if isinstance(item, Email)
        ]
        if not drafted:
            # Every candidate failed, which makes it the format and not the
            # angle. Surface the first failure rather than a summary of four.
            raise next(item for item in written if isinstance(item, BaseException))
        for failure in (item for item in written if isinstance(item, BaseException)):
            logger.info("craft: one candidate for email %d failed - %s", brief.position, failure)

        kept, duplicates = _distinct(drafted)
        for idea, _ in duplicates:
            logger.info(
                "craft: email %d candidate %r came back as one already drafted - dropped",
                brief.position,
                idea,
            )
        for _, draft in kept:
            self._observer.on_draft(brief.position, 1, draft)
        self._observer.on_role_finished(
            "email_writer",
            f"{len(kept)} candidate(s): "
            + "; ".join(f'"{draft.subject}"' for _, draft in kept)
            + (
                f" ({len(duplicates)} came back as a repeat and was dropped before it was read)"
                if duplicates
                else ""
            ),
            {"subjects": [draft.subject for _, draft in kept], "dropped": len(duplicates)},
        )

        checked = [self._check(draft, brief, previous) for _, draft in kept]
        # A candidate a blocking gate has already vetoed cannot win this
        # bake-off however well it reads: `EmailVersion.measured` puts the gate
        # first and the score second, so the comparison is settled before
        # anybody is asked. Reading one anyway buys a whole panel per blocked
        # draft to produce a number nothing downstream consumes - three readers
        # each, on a preset that writes four candidates. The gates already ran
        # before anything was paid for; acting on what they said is the other
        # half of that, and it was missing.
        #
        # Unless every candidate is blocked, in which case the gates have said
        # nothing about *which* to keep and the cold read is the only
        # instrument left that can.
        readable = [index for index, (gates, _) in enumerate(checked) if not gates.blocking]
        if not readable:
            readable = list(range(len(kept)))
        vetoed = len(kept) - len(readable)
        self._observer.on_role_started(
            "blind_reader",
            f"Email {brief.position} · {len(readable)} candidate(s) read cold by "
            f"{len(self._personas)} reader(s)"
            + (
                f" ({vetoed} broke an automatic check and cannot win - not read)"
                if vetoed
                else ""
            ),
            {
                "position": brief.position,
                "attempt": 1,
                "candidates": len(readable),
                "vetoed": vetoed,
            },
        )
        reported = await asyncio.gather(
            *(self._reader.read(kept[index][1], self._personas) for index in readable)
        )
        reads: list[PanelRead] = [PanelRead() for _ in kept]
        for index, read in zip(readable, reported, strict=True):
            reads[index] = read
        candidates = [
            EmailVersion(
                attempt=1,
                email=draft,
                gates=gate,
                substantiation=substantiation,
                read=read,
                idea=idea,
            )
            for (idea, draft), (gate, substantiation), read in zip(
                kept, checked, reads, strict=True
            )
        ]
        # `max` keeps the first of equal candidates, so the drafts stay ranked
        # in the order they were written when nothing separates them - which is
        # the order the strategist ranked the ideas in.
        winner = max(candidates, key=lambda item: item.measured)
        self._observer.on_role_finished(
            "blind_reader",
            "Candidates scored "
            + ", ".join(f"{reads[index].pull:.0f}/10" for index in readable)
            + f' - kept "{winner.email.subject}"',
            {
                "pull": winner.read.pull,
                "scores": [reads[index].pull for index in readable],
            },
        )
        losers = [item for item in candidates if item is not winner]
        winner = await self._run_off(winner, losers, brief)
        losers = [item for item in candidates if item is not winner]
        # Announced for the winner only: these are the readings the rest of
        # the loop actually works from, and the timeline is a record of what
        # happened to the email that shipped.
        self._observer.on_gates(brief.position, 1, winner.gates)
        self._observer.on_read(brief.position, 1, winner.read)
        return (
            winner.email,
            (winner.gates, winner.substantiation, winner.read),
            losers,
            winner.idea,
        )

    async def _run_off(
        self, winner: EmailVersion, losers: list[EmailVersion], brief: EmailBrief
    ) -> EmailVersion:
        """The two best candidates, put in front of the reader together.

        The scores have already ranked the field, and between the top two they
        routinely cannot: a bake-off whose candidates come back 5, 5 and 4 has
        told us which one to throw away and nothing about the other two. That
        is the comparison worth one more reaction, and only that one - running
        the whole field pairwise costs a call per pair to re-answer a question
        the scores have already settled for the bottom of it.
        """
        if self._judge is None or not losers:
            return winner
        runner_up = max(losers, key=lambda item: item.measured)
        if winner.measured[0] != runner_up.measured[0]:
            return winner
        self._observer.on_role_started(
            "preference_judge",
            f"Email {brief.position} · the two best candidates, read side by side",
            {"position": brief.position, "attempt": 1},
        )
        duel = await self._judge.duel(
            challenger=runner_up.email, champion=winner.email, personas=self._personas
        )
        runner_up.duel = duel
        self._observer.on_role_finished(
            "preference_judge",
            f'"{runner_up.email.subject}" vs "{winner.email.subject}" - {duel.render()}',
            {"challenger_won": duel.challenger_wins},
        )
        return runner_up if duel.challenger_wins else winner

    async def _prefers(
        self, challenger: EmailVersion, champion: EmailVersion, brief: EmailBrief
    ) -> bool:
        """Whether the new version replaces the one that held the title.

        Gates first and deterministically: a draft making an unsupported claim
        does not get to win a popularity contest. Past that the question is
        which one a reader would act on, and that is a choice between two
        concrete emails rather than a comparison of two numbers - which is the
        change that makes "did this rewrite help" answerable at all. Without a
        judge the loop falls back to the numbers, and to the old rule that a
        tie leaves the incumbent standing.

        The second deterministic rule is the mirror of the first, and it exists
        because the judge was measured and could not see it. On the bench, an
        email with its whole proof paragraph deleted - nothing invented, no
        gate tripped, every remaining claim now unbacked - took half the votes
        against the original. So a rewrite that carries strictly less of what
        this email was built on does not take the title, whatever the ballot
        says: the vote is a measurement of an instrument that has been shown
        blind to exactly this, and losing the evidence is not a matter of
        taste. Adding proof is never blocked, and a rewrite that trades one
        support for another is not weaker - see `Substantiation.weaker_than`.
        """
        if bool(challenger.gates.blocking) is not bool(champion.gates.blocking):
            return not challenger.gates.blocking
        if challenger.substantiation.weaker_than(champion.substantiation):
            logger.info(
                "craft: email %d attempt %d dropped evidence the version before it carried "
                "- not taking the title",
                brief.position,
                challenger.attempt,
            )
            self._observer.on_phase(
                "craft",
                f"Email {brief.position}: rewrite {challenger.attempt - 1} left out proof the "
                "version before it had on the page - keeping the one that argues from the "
                "material",
                {
                    "position": brief.position,
                    "attempt": challenger.attempt,
                    "carried": list(challenger.substantiation.carried),
                    "was_carrying": list(champion.substantiation.carried),
                },
            )
            return False
        if self._judge is not None and challenger.read.has_verdict and champion.read.has_verdict:
            self._observer.on_role_started(
                "preference_judge",
                f"Email {brief.position} · rewrite {challenger.attempt - 1} read against the "
                "version it would replace",
                {"position": brief.position, "attempt": challenger.attempt},
            )
            duel = await self._judge.duel(
                challenger=challenger.email, champion=champion.email, personas=self._personas
            )
            challenger.duel = duel
            self._observer.on_role_finished(
                "preference_judge",
                duel.render(),
                {"challenger_won": duel.challenger_wins},
            )
            if duel.decided:
                return duel.challenger_wins
        return challenger.measured > champion.measured

    def _pivot_idea(self, outcome: EmailOutcome) -> str:
        """The best claim this email has not tried yet, or nothing.

        One pivot per email. A second one is a campaign whose brief was wrong
        about who it is writing to, and no amount of re-arguing fixes that -
        it goes on the receipt instead, where the user can act on it.
        """
        if outcome.pivoted_to:
            return ""
        tried = {
            normalized(version.idea)
            for version in [*outcome.versions, *outcome.discarded]
            if version.idea
        }
        tried.add(normalized(outcome.brief.single_idea))
        return next(
            (
                idea
                for idea in outcome.brief.alternative_ideas
                if normalized(idea) not in tried
            ),
            "",
        )

    async def _pivot_draft(
        self,
        outcome: EmailOutcome,
        brief: EmailBrief,
        campaign: CampaignBrief,
        request: CampaignRequest,
        previous: list[Email],
        attempt: int,
        idea: str,
    ) -> tuple[Email, str]:
        """A fresh draft on a different claim - not a rewrite of the old one.

        Deliberately not routed through `_revise`: a rewrite is handed the
        draft it is replacing and told to keep what worked, which is exactly
        the instruction that would drag the argument that has just been
        measured twice into the one that has not been tried at all.
        """
        self._observer.on_role_started(
            "email_writer",
            f"Email {brief.position} · a different argument",
            {"position": brief.position, "attempt": attempt, "idea": idea},
        )
        draft = await self._writer.draft(
            brief=brief,
            campaign=campaign,
            request=request,
            artifacts=self._artifacts,
            previous=previous,
            idea_override=idea,
            history=_history(outcome.versions, outcome.discarded),
        )
        self._observer.on_draft(brief.position, attempt, draft)
        self._observer.on_role_finished(
            "email_writer", f'Drafted "{draft.subject}"', {"subject": draft.subject}
        )
        return draft, idea

    def _announce_stall(self, brief: EmailBrief, attempt: int) -> None:
        logger.info(
            "craft: email %d attempt %d was not preferred to the version before it - stopping",
            brief.position,
            attempt,
        )
        # Deliberately does not name the reader. A rewrite fails to take the
        # title either because a reader preferred the incumbent or because it
        # dropped the proof the incumbent carried, and the second one is
        # announced by `_prefers` on the line above this. Saying "the reader
        # preferred" in both cases attributes a deterministic decision to a
        # vote nobody cast.
        self._observer.on_phase(
            "craft",
            f"Email {brief.position}: rewrite {attempt - 1} was not preferred to the version "
            f"before it - stopping rather than spending "
            f"{self._max_revisions - attempt + 1} more rewrite(s) on it",
            {
                "position": brief.position,
                "attempt": attempt,
                "rewrites_left": self._max_revisions - attempt + 1,
            },
        )

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
            brief=brief if not version.idea else brief.model_copy(
                update={"single_idea": version.idea}
            ),
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

    async def _judge_draft(
        self,
        draft: Email,
        brief: EmailBrief,
        attempt: int,
        previous: list[Email],
        screened: tuple[GateReport, Substantiation, PanelRead] | None = None,
        idea: str = "",
    ) -> EmailVersion:
        """Free checks first, then the cold reader.

        The order is a cost decision as much as a quality one: the gates cost
        nothing and catch the failures that would make every later opinion
        moot, so they run before anything is paid for. `screened` is that same
        pair already bought during the bake-off, for the one draft that won it.

        The critic is not here any more. It used to run inside this method, on
        every attempt, before anybody had decided whether a rewrite would
        follow - so on the attempt where the loop then stopped, its whole
        output was edits for a pass that never happened. It is bought by the
        caller, after that decision.
        """
        if screened is not None:
            gates, substantiation, read = screened
        else:
            gates, substantiation = self._check(draft, brief, previous)
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
        return EmailVersion(
            attempt=attempt,
            email=draft,
            gates=gates,
            substantiation=substantiation,
            read=read,
            idea=idea or brief.single_idea,
        )

    async def _critique(
        self, version: EmailVersion, brief: EmailBrief, campaign: CampaignBrief, attempt: int
    ) -> Critique | None:
        if self._critic is None:
            return None
        self._observer.on_role_started(
            "conversion_critic",
            f"Email {brief.position} · conversion critique",
            {"position": brief.position, "attempt": attempt},
        )
        critique = await self._critic.critique(
            email=version.email,
            brief=brief,
            campaign=campaign,
            artifacts=self._artifacts,
            read=version.read,
            gates=version.gates,
            substantiation=version.substantiation,
        )
        self._observer.on_critique(brief.position, attempt, critique)
        self._observer.on_role_finished(
            "conversion_critic",
            f"{critique.verdict} - {len(critique.edits)} edit(s) requested",
            {"verdict": critique.verdict},
        )
        return critique

    async def _critique_for_the_record(
        self, outcome: EmailOutcome, brief: EmailBrief, campaign: CampaignBrief
    ) -> None:
        """One critique on a run that never bought one.

        A run configured for no rewrites at all would otherwise never critique
        anything, and the critique is not only an instruction to the writer:
        its brief drift and unspent evidence are what the user is shown about
        why an email is the way it is, and an email with no judgment on the
        record at all is a worse deliverable than a critique nobody could act
        on. This is the only place a critique is knowingly bought after the
        outcome is decided, and it happens at most once per email.
        """
        if self._critic is None or any(version.critic_judged for version in outcome.versions):
            return
        best = outcome.best
        best.critique = await self._critique(best, brief, campaign, best.attempt)

    async def _polish_subject(
        self, outcome: EmailOutcome, brief: EmailBrief, previous: list[Email]
    ) -> None:
        """The last thing that happens to an email, and the only one after it
        has been judged.

        Placed here because the subject is the one part of the deliverable the
        rest of the loop cannot improve - every rewrite replaces it as a
        by-product of replacing the body - and because there is no point paying
        to optimise the line on a draft that is about to be thrown away.

        The body is untouched, so the reading already on the record still
        describes what ships. It describes it conservatively: the pull that was
        measured was measured with the subject the body arrived with, and this
        step only ever swaps in a line more of a hundred people would open.

        Every alternative is gated *before* it is read, because a subject can
        repeat an earlier email's word for word or carry a figure the ledger
        does not license. That used to happen afterwards: the broken line was
        scanned at full price, could win the field, and was then reverted - so
        the email kept the line it started with even when a clean alternative
        had scanned better than it. Screening first costs the same and makes
        the winner takeable.
        """
        if self._subjects is None or self._subject_variants < 1:
            return
        best = outcome.best
        # Checked once per distinct line: the screen and the swap that follows
        # it ask the same question of the same email, and `_check` walks the
        # ledger and the whole sequence to answer it.
        checked: dict[tuple[str, str], tuple[GateReport, Substantiation]] = {}

        def check(candidate: Email) -> tuple[GateReport, Substantiation]:
            key = (candidate.subject, candidate.preview_text)
            if key not in checked:
                checked[key] = self._check(candidate, brief, previous)
            return checked[key]

        def clean(candidate: Email) -> bool:
            # A draft that was already blocked cannot be made worse by a
            # subject that is blocked too, and screening those out would leave
            # the field empty on exactly the emails most in need of a better
            # line. Only a line that breaks something the draft had not is out.
            gates, _ = check(candidate)
            return not gates.blocking or bool(best.gates.blocking)

        self._observer.on_role_started(
            "subject_writer",
            f"Email {brief.position} · {self._subject_variants} alternative subject lines",
            {"position": brief.position, "variants": self._subject_variants},
        )
        improved, summary = await self._subjects.improve(
            email=best.email,
            brief=brief,
            artifacts=self._artifacts,
            personas=self._personas,
            variants=self._subject_variants,
            screen=clean,
        )
        self._observer.on_role_finished("subject_writer", summary, {"subject": improved.subject})
        if improved.subject == best.email.subject:
            return
        best.email = improved
        best.gates, best.substantiation = check(improved)


def _bets(brief: EmailBrief, candidates: int) -> list[tuple[str, str]]:
    """What each candidate argues, and where it starts.

    The brief's own idea is always the first bet - it is the one the strategist
    chose with everything in front of it, and a bake-off that does not include
    it is not testing the strategy, it is replacing it. After that come the
    alternatives it named, best first, each on a different opening move.

    Where there are fewer alternatives than candidates the remaining drafts
    fall back to the brief's idea on an unused opening move, which is what this
    function did in its entirety before the brief carried alternatives.
    """
    ideas = [brief.single_idea, *brief.alternative_ideas][:candidates]
    ideas += [brief.single_idea] * (candidates - len(ideas))
    return list(zip(ideas, _OPENING_MOVES[:candidates], strict=True))


def _distinct(
    drafted: list[tuple[str, Email]],
) -> tuple[list[tuple[str, Email]], list[tuple[str, Email]]]:
    """Candidates that are actually different, and the repeats.

    A bake-off exists to buy alternatives, and two drafts with the same subject
    or the same first sentence are one alternative bought twice. Screened here,
    before the cold reads, because the reads are what the duplicates would cost
    - in a measured run two of three candidates came back with the same subject
    line and each was read at full price to establish that they scored the
    same.

    Kept in the order they were written, and the first of any group survives:
    the candidates are ranked by the strategist and the earlier one is the
    better-ranked bet.
    """
    kept: list[tuple[str, Email]] = []
    repeats: list[tuple[str, Email]] = []
    seen_subjects: set[str] = set()
    seen_openings: set[str] = set()
    for idea, draft in drafted:
        subject = normalized(draft.subject)
        opening = " ".join(normalized(_opening_line(draft)).split()[:_SAME_OPENING_WORDS])
        if subject in seen_subjects or (opening and opening in seen_openings):
            repeats.append((idea, draft))
            continue
        seen_subjects.add(subject)
        seen_openings.add(opening)
        kept.append((idea, draft))
    return kept, repeats
