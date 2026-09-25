"""How good are the judges? Answered without a single user.

    python -m app.evaluation.judge_bench --dry-run          # spends nothing
    python -m app.evaluation.judge_bench --out eval/judges   # spends quota

Every other measurement in this package grades the *copy*. This one grades the
*instruments*, and it is the measurement the others rest on: `record.py`
reports average pull, `head_to_head.py` counts votes, and the craft loop ships
whichever version a duel preferred. If those judges cannot tell a specific
email from a vague one, every number downstream is a number about nothing, and
nothing in a run would look wrong.

The trick that makes it free of users is in `mutations.py`: pairs whose winner
is known by construction. The original is a hand-written control from the
golden set - deliberately good, deliberately not a showpiece - and the mutant
is the same email with one principle broken. The judge is asked to choose. It
should choose the original, every time, and the share of the time it does is
the reliability of the instrument the whole system is steered by.

Three things make the answer worth trusting.

**Ties are not catches.** A judge that cannot separate the pair has failed to
detect the damage, however diplomatically. Detection counts strict wins only.

**One persona, several votes.** The craft loop varies the reader to cover an
audience; this varies nothing, because it is measuring the instrument and not
the market. Repeated votes from one persona with the ballot order alternating
isolate judge reliability from persona variance - the same reason
`tournament.py` alternates labels in the first place.

**There is a control arm.** A judge that always picks the first email scores
perfectly on damage it never noticed. The invariant pairs - an email against
itself, and against a copy with a different greeting - are what expose that:
they should come back near even, and a lopsided result there discounts every
detection scored elsewhere.

What this cannot tell you is whether the copy is any good; `head_to_head.py`
does that, and it needs a human control. This says whether the thing that
decides what ships can see what it is deciding about.
"""

import argparse
import asyncio
import logging
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

from app.ai.factory import get_ai_provider
from app.ai.model_router import ModelRouter
from app.ai.models import ClaudeModel
from app.core.config import PROMPTS_DIR
from app.evaluation.controls import BenchSource, bench_only_sources
from app.evaluation.golden import GOLDEN_CASES, GoldenCase
from app.evaluation.mutations import (
    HARD_MUTATIONS,
    MUTATIONS,
    Mutation,
    mutation_named,
)
from app.marketing.email_copy import Email, EmailCopyError, parse_email, render_email
from app.marketing.gates import (
    GateReport,
    placeholder_gate,
    spam_gate,
    stock_phrase_gate,
    structure_gate,
)
from app.marketing.reader import BlindReader
from app.marketing.subject_lines import SubjectBakeOff, SubjectOption
from app.marketing.tournament import PreferenceJudge
from app.runtime.events import EventBus
from app.runtime.exceptions import ProviderError
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import get_prompt_engine

logger = logging.getLogger("marketingos.evaluation")

#: Votes per pair. Four rather than two because a 2-0 is one reader twice and
#: reads the same as a coin landing the same way twice; four is the smallest
#: ballot where an even split and a clean sweep are visibly different results.
DEFAULT_VOTES = 4

#: No model override by default, on purpose. `preference_judge` and
#: `blind_reader` ask for a tier and the router maps it - so leaving it alone
#: benches whatever those roles resolve to *today*, which is the instrument
#: that actually decides what ships. Pinning a model here would measure a judge
#: the system never runs, and would go stale the day the tier map moves.
#:
#: A tier name is not a model name: `ModelRouter` overrides are passed straight
#: through to the CLI as the model, so "balanced" reaches Claude Code as a
#: model id, which it rejects. `--judge-model` is validated against
#: `ClaudeModel` before anything is billed.
DEFAULT_JUDGE_MODEL: str | None = None


def _subject_only(original: Email, mutant: Email) -> bool:
    """Whether the damage is entirely above the body.

    Derived rather than declared on the `Mutation`, because it is a property of
    what a mutation *did* to this email and code can see it: two emails that
    render identically once their subject and preview are made the same differ
    in nothing else.

    It decides which instrument is asked. A duel shows a reader two whole
    emails and asks which they would act on - both are already open by then, so
    the subject barely enters into it, and a pair identical below the subject
    line comes back an even split whatever the lines say. That is not the judge
    failing to see damage; it is the wrong judge. The system already has the
    right one: the inbox scanner, which is shown lines with no bodies, because
    that is the decision a recipient actually makes.
    """
    if original.subject == mutant.subject and original.preview_text == mutant.preview_text:
        return False
    levelled = mutant.model_copy(
        update={"subject": original.subject, "preview_text": original.preview_text}
    )
    return render_email(levelled) == render_email(original)


def _free_gates(email: Email) -> GateReport:
    """The checks that need no compiled knowledge.

    Evidence, overlap and call-to-action are left out on purpose: each needs a
    ledger or an offer sheet the bench has not compiled, and an evidence gate
    run against an empty ledger flags every figure in the *original* too - it
    would report damage where there is none.
    """
    text = render_email(email)
    report = GateReport()
    for part in (
        structure_gate(email),
        placeholder_gate(text),
        stock_phrase_gate(text),
        spam_gate(email),
    ):
        report = report.extend(part)
    return report


@dataclass(frozen=True)
class PairResult:
    """One original, one mutant, and what the instruments made of them."""

    source: str
    mutation: Mutation
    #: True when the original is a control a person wrote. Carried on the pair
    #: rather than looked up later so a report assembled from pairs alone -
    #: which is how the tests build one - still knows which rate each belongs
    #: in. See `controls.py` for why the two are never pooled.
    anchor: bool = False
    #: Set when the pair was never judged - the mutation was a no-op on this
    #: email, so there was no damage to detect and scoring it either way would
    #: be a lie about the judge.
    skipped: str = ""
    original_votes: int = 0
    mutant_votes: int = 0
    unreported: int = 0
    reasons: tuple[str, ...] = ()
    #: None when the reader was not run. Distinct from 0.0, which is a score.
    original_pull: float | None = None
    mutant_pull: float | None = None
    gate_issues: tuple[str, ...] = ()
    #: Opens in a hundred, when this pair was scored in an inbox rather than
    #: duelled - see `_subject_only`. None means the inbox arm did not run.
    original_opens: float | None = None
    mutant_opens: float | None = None

    @property
    def by_inbox(self) -> bool:
        return self.original_opens is not None and self.mutant_opens is not None

    @property
    def cast(self) -> int:
        return self.original_votes + self.mutant_votes

    @property
    def decided(self) -> bool:
        return not self.skipped and (self.cast > 0 or self.by_inbox)

    @property
    def caught(self) -> bool:
        """Strictly preferred the original. A tie is a miss - see the module
        docstring: a judge that cannot separate the pair has not detected the
        damage, it has declined to.

        The inbox arm is held to the same rule for the same reason: two lines
        the scanner expects the same number of opens from are two lines it
        could not separate.
        """
        if self.by_inbox:
            return self.original_opens > self.mutant_opens
        return self.decided and self.original_votes > self.mutant_votes

    @property
    def separated(self) -> bool:
        """Whether the cold reader's absolute score moved the right way.

        Its own module warns that these scores saturate. This is the line that
        says by how much, on damage that is not in question.
        """
        if self.original_pull is None or self.mutant_pull is None:
            return False
        return self.original_pull > self.mutant_pull

    @property
    def lean(self) -> int:
        """How far off an even split, for the invariant pairs. Zero is the
        answer; anything else is the judge moving on something other than
        quality."""
        return abs(self.original_votes - self.mutant_votes)

    def render(self) -> str:
        if self.skipped:
            return f"  · {self.mutation.name:<24} {self.source:<16} skipped - {self.skipped}"
        if self.mutation.invariant:
            verdict = "even" if self.lean == 0 else f"leans {self.lean}"
        else:
            verdict = "caught" if self.caught else "MISSED"
        mark = "·" if self.mutation.invariant else ("✓" if self.caught else "✗")
        # An inbox pair has no ballot, so the column that holds one says what
        # was asked instead - printing 0-0 there would read as a duel nobody
        # could judge, which is a different result entirely.
        tally = "in inbox" if self.by_inbox else f"{self.original_votes}-{self.mutant_votes}"
        line = f"  {mark} {self.mutation.name:<24} {self.source:<16} {tally:<8}  {verdict}"
        if self.by_inbox:
            line += f"   opens {self.original_opens:.0f} vs {self.mutant_opens:.0f} in 100"
        if self.original_pull is not None and self.mutant_pull is not None:
            line += f"   pull {self.original_pull:.0f} → {self.mutant_pull:.0f}"
        if self.gate_issues:
            line += f"   gates: {len(self.gate_issues)}"
        if self.unreported:
            line += f"   ({self.unreported} vote(s) did not come back)"
        return line


#: Two-sided 95%. The bench is small and will stay small - every pair is
#: billed - so the interval is not decoration here, it is the difference
#: between "the judge improved" and "four votes landed the other way".
_Z = 1.96


def wilson(successes: int, trials: int, z: float = _Z) -> tuple[float, float]:
    """A confidence interval that stays inside [0, 1] at these sample sizes.

    The normal approximation everybody reaches for first gives 4/4 an interval
    of exactly 4/4, which is the one answer a bench of four votes can never
    support. Wilson's score interval does not collapse at the ends and does
    not run off past 0 or 1, which is the whole reason to print one: the first
    round's headline was 4/6, and 4/6 with six pairs is consistent with a judge
    that is right nine times in ten and one that is guessing.
    """
    if trials <= 0:
        return (0.0, 1.0)
    rate = successes / trials
    denominator = 1 + z * z / trials
    centre = (rate + z * z / (2 * trials)) / denominator
    spread = z * math.sqrt(rate * (1 - rate) / trials + z * z / (4 * trials * trials))
    half = spread / denominator
    return (max(0.0, centre - half), min(1.0, centre + half))


@dataclass(frozen=True)
class ItemResult:
    """How one control email fared, across every mutation applied to it.

    The number this bench was rebuilt to produce. A detection rate pooled over
    items answers "can the judge read", and cannot answer "can the judge read
    *this*" - so a miss on a single-item bench is unattributable, and the first
    round's 2-2 on a stripped proof paragraph is still, today, either a blind
    judge or an email whose proof was not carrying much. Reading the same
    mutation down a column of items is what separates them.
    """

    source: str
    anchor: bool
    caught: int
    judged: int
    #: Ballots that went to the original, and ballots cast, over this item's
    #: judgment-only pairs. Finer than caught/judged on purpose: 4-0 and 3-1
    #: are both catches and are not the same evidence, and an item sitting at
    #: half its ballots is one no judge could separate rather than one this
    #: judge failed on.
    original_ballots: int = 0
    ballots: int = 0

    @property
    def rate(self) -> float:
        return self.caught / self.judged if self.judged else 0.0

    @property
    def ballot_share(self) -> float:
        return self.original_ballots / self.ballots if self.ballots else 0.5


@dataclass(frozen=True)
class MutationResult:
    """How one kind of damage fared, across every item it was applied to.

    The actionable half. "The judge misses `bury_the_ask`" is a sentence
    somebody can act on - by changing the duel prompt, or by moving the check
    into code the way `strip_the_proof` already was. "The judge scores 67%" is
    not a sentence about anything.
    """

    mutation: Mutation
    caught: int
    judged: int
    missed_on: tuple[str, ...] = ()

    @property
    def rate(self) -> float:
        return self.caught / self.judged if self.judged else 0.0


@dataclass
class BenchReport:
    votes_per_pair: int = DEFAULT_VOTES
    pairs: list[PairResult] = field(default_factory=list)

    def _of(self, *, invariant: bool, gate_visible: bool | None = None) -> list[PairResult]:
        return [
            pair
            for pair in self.pairs
            if pair.mutation.invariant is invariant
            and (gate_visible is None or pair.mutation.gate_visible is gate_visible)
            and pair.decided
            and not pair.by_inbox
        ]

    @staticmethod
    def _rate(pairs: list[PairResult]) -> float:
        return sum(1 for pair in pairs if pair.caught) / len(pairs) if pairs else 0.0

    @property
    def judgment_only(self) -> list[PairResult]:
        return self._of(invariant=False, gate_visible=False)

    @property
    def gate_visible(self) -> list[PairResult]:
        return self._of(invariant=False, gate_visible=True)

    @property
    def by_inbox(self) -> list[PairResult]:
        """Pairs the inbox scanner ranked instead of the judge duelling them.

        Their own section rather than folded into the judgment-only rate,
        because they measure a different instrument. Folding them in is what
        made the first round read 4/6: the sixth pair was two identical bodies
        under different subject lines, handed to a judge that is shown whole
        emails, and it could only ever come back even.
        """
        return [
            pair
            for pair in self.pairs
            if pair.by_inbox and not pair.mutation.invariant and pair.decided
        ]

    @property
    def inbox_detection_rate(self) -> float:
        return self._rate(self.by_inbox)

    @property
    def invariants(self) -> list[PairResult]:
        return self._of(invariant=True)

    @property
    def detection_rate(self) -> float:
        """The headline. Share of judgment-only damage the judge preferred the
        original on - the reliability of the instrument that decides what
        ships, on the failures only judgment can catch."""
        return self._rate(self.judgment_only)

    @property
    def gate_detection_rate(self) -> float:
        return self._rate(self.gate_visible)

    @property
    def separation_rate(self) -> float:
        graded = [
            pair
            for pair in self.pairs
            if not pair.mutation.invariant and pair.original_pull is not None
        ]
        return (
            sum(1 for pair in graded if pair.separated) / len(graded) if graded else 0.0
        )

    @property
    def sources(self) -> list[str]:
        """Item names, in the order they were benched."""
        ordered: list[str] = []
        for pair in self.pairs:
            if pair.source not in ordered:
                ordered.append(pair.source)
        return ordered

    def _judgment_for(self, source: str) -> list[PairResult]:
        return [pair for pair in self.judgment_only if pair.source == source]

    def items(self) -> list[ItemResult]:
        """One row per control email."""
        rows: list[ItemResult] = []
        for name in self.sources:
            scored = self._judgment_for(name)
            if not scored:
                continue
            rows.append(
                ItemResult(
                    source=name,
                    anchor=scored[0].anchor,
                    caught=sum(1 for pair in scored if pair.caught),
                    judged=len(scored),
                    original_ballots=sum(pair.original_votes for pair in scored),
                    ballots=sum(pair.cast for pair in scored),
                )
            )
        return rows

    def by_mutation(self) -> list[MutationResult]:
        """One row per kind of damage, over every item it reached."""
        rows: list[MutationResult] = []
        for mutation in dict.fromkeys(pair.mutation for pair in self.judgment_only):
            scored = [pair for pair in self.judgment_only if pair.mutation is mutation]
            rows.append(
                MutationResult(
                    mutation=mutation,
                    caught=sum(1 for pair in scored if pair.caught),
                    judged=len(scored),
                    missed_on=tuple(pair.source for pair in scored if not pair.caught),
                )
            )
        return sorted(rows, key=lambda row: (row.rate, row.mutation.name))

    def _anchored(self, anchor: bool) -> list[PairResult]:
        return [pair for pair in self.judgment_only if pair.anchor is anchor]

    @property
    def anchor_detection_rate(self) -> float:
        """The rate on the controls a person wrote.

        Reported beside the pooled number rather than folded into it. The rest
        of the set was written for this bench, and copy written the same way
        the judge thinks may be easier to defend than copy a person wrote - so
        if these two diverge, the suspect is `controls.py`, not the judge.
        """
        return self._rate(self._anchored(True))

    @property
    def bench_detection_rate(self) -> float:
        return self._rate(self._anchored(False))

    @property
    def interval(self) -> tuple[float, float]:
        caught = sum(1 for pair in self.judgment_only if pair.caught)
        return wilson(caught, len(self.judgment_only))

    @property
    def noise(self) -> float:
        """Average distance from an even split on pairs that are not damaged.

        Zero is a judge reading the copy. The ballot already alternates label
        order, so anything much above zero is the instrument answering from
        something other than what is on the page.
        """
        pairs = self.invariants
        return sum(pair.lean for pair in pairs) / len(pairs) if pairs else 0.0

    def _legend(self) -> list[str]:
        rows = self.items()
        return [
            "  items: "
            + "   ".join(
                f"[{index}] {row.source}" + (" *" if row.anchor else "")
                for index, row in enumerate(rows, 1)
            ),
            "         * written by a person; the rest were written for the bench",
        ]

    def _matrix(self) -> list[str]:
        """Damage down the rows, items across the columns.

        The one view the old report could not produce, because it had a single
        column. A row of crosses is a blind spot in the judge, and belongs in
        the duel prompt or - better - in code, the way `strip_the_proof` ended
        up in `substantiation.py`. A column of crosses is a control that is not
        carrying what the mutations remove, and belongs in `controls.py`.
        Pooled into one percentage the two are indistinguishable, which is what
        made the first round's 4/6 unactionable.
        """
        rows = self.items()
        if len(rows) < 2:
            return []
        lines = [
            "\nMATRIX  (judgment-only damage - \u2713 caught, \u2717 missed, \u00b7 not judged)",
            "",
            "  " + " " * 26
            + "".join(f"{index:>3}" for index in range(1, len(rows) + 1))
            + "   caught",
        ]
        for result in self.by_mutation():
            seen = {
                pair.source: pair.caught
                for pair in self.judgment_only
                if pair.mutation is result.mutation
            }
            cells = "".join(
                "  " + ("\u2713" if seen[row.source] else "\u2717")
                if row.source in seen
                else "  \u00b7"
                for row in rows
            )
            lines.append(
                f"  {result.mutation.name:<26}{cells}   {result.caught}/{result.judged}"
            )
        lines.append("")
        lines.extend(self._legend())
        return lines

    def _per_item(self) -> list[str]:
        rows = self.items()
        if len(rows) < 2:
            return []
        lines = ["\nPER ITEM  (judgment-only)"]
        for index, row in enumerate(rows, 1):
            origin = "person" if row.anchor else "bench"
            lines.append(
                f"  [{index}] {row.source:<20}{origin:<8}{row.caught}/{row.judged}"
                f"   ballots to the original {row.ballot_share:.0%}"
            )
        lines.append(
            "  An item whose ballots sit near 50% is one nothing separated. Read that as a "
            "control\n  that is not carrying what the mutation removes, before reading it as "
            "a judge that cannot see."
        )
        return lines

    def _per_mutation(self) -> list[str]:
        rows = self.by_mutation()
        if not rows or len(self.items()) < 2:
            return []
        lines = ["\nPER MUTATION  (judgment-only, worst first)"]
        for result in rows:
            line = (
                f"  {result.mutation.name:<26}{result.caught}/{result.judged} "
                f"({result.rate:.0%})"
            )
            if result.missed_on:
                line += f"   missed on: {', '.join(result.missed_on)}"
            lines.append(line)
        return lines

    def render(self) -> str:
        anchors = len({pair.source for pair in self.pairs if pair.anchor})
        lines = [
            (
                f"Judge bench - {len({pair.source for pair in self.pairs})} source email(s) "
                f"({anchors} written by a person), {len(self.pairs)} pair(s), "
                f"{self.votes_per_pair} votes each"
            ),
        ]
        for title, pairs, note in (
            ("JUDGMENT-ONLY", self.judgment_only, "nothing mechanical can catch these"),
            ("GATE-VISIBLE", self.gate_visible, "the free checks should catch these too"),
            ("INBOX", self.by_inbox, "damage above the body - ranked as lines, not duelled"),
            ("INVARIANCE", self.invariants, "the verdict should not move"),
        ):
            if not pairs:
                continue
            lines.append(f"\n{title}  ({note})")
            lines.extend(pair.render() for pair in pairs)

        skipped = [pair for pair in self.pairs if pair.skipped]
        if skipped:
            lines.append("\nNOT JUDGED  (no damage to detect, or the call failed)")
            lines.extend(pair.render() for pair in skipped)

        lines.extend(self._matrix())
        lines.extend(self._per_item())
        lines.extend(self._per_mutation())

        low, high = self.interval
        lines.append("\nDetection")
        lines.append(
            f"  judgment-only   {sum(1 for p in self.judgment_only if p.caught)}"
            f"/{len(self.judgment_only)} ({self.detection_rate:.0%})"
            f"  [95% CI {low:.0%}-{high:.0%}]   <- the number that matters"
        )
        if self._anchored(True) and self._anchored(False):
            lines.append(
                f"    on the {len({p.source for p in self._anchored(True)})} control(s) a person "
                f"wrote   {self.anchor_detection_rate:.0%}"
            )
            lines.append(
                f"    on the {len({p.source for p in self._anchored(False)})} written for the "
                f"bench    {self.bench_detection_rate:.0%}"
                "   (a gap here indicts the fixtures, not the judge)"
            )
        if self.gate_visible:
            lines.append(
                f"  gate-visible    {sum(1 for p in self.gate_visible if p.caught)}"
                f"/{len(self.gate_visible)} ({self.gate_detection_rate:.0%})"
            )
        if self.by_inbox:
            lines.append(
                f"  inbox           {sum(1 for p in self.by_inbox if p.caught)}"
                f"/{len(self.by_inbox)} ({self.inbox_detection_rate:.0%})   "
                "<- the subject decision, asked of the scanner rather than the judge"
            )
        graded = [p for p in self.pairs if not p.mutation.invariant and p.original_pull is not None]
        if graded:
            lines.append(
                f"  reader ranked the original higher in {sum(1 for p in graded if p.separated)}"
                f"/{len(graded)} pair(s) ({self.separation_rate:.0%})"
            )
        if self.invariants:
            leaning = [pair for pair in self.invariants if pair.lean]
            lines.append(
                f"\nNoise floor\n  {len(self.invariants)} undamaged pair(s): "
                f"{len(self.invariants) - len(leaning)} even, {len(leaning)} leaning "
                f"(average lean {self.noise:.1f}; 0 is a judge reading the copy)"
            )
            # Named rather than counted: a judge that sweeps an email against
            # itself discounts every detection it scored elsewhere, and the
            # first question is always which item it did that on.
            lines.extend(
                f"    {pair.source} / {pair.mutation.name}: "
                f"{pair.original_votes}-{pair.mutant_votes}"
                for pair in leaning
            )
        return "\n".join(lines)


# --------------------------------------------------------------------- run


def bench_sources(
    cases: tuple[GoldenCase, ...] = GOLDEN_CASES, *, anchors_only: bool = False
) -> list[BenchSource]:
    """The originals, and who reads them.

    Two families, kept apart all the way into the report. The golden set's
    controls are the **anchors**: a person wrote them, so how hard they are to
    defend is independent of the thing being measured. `controls.py` supplies
    the rest, and they exist because two items cannot tell a blind judge from
    an easy email - with one item, a 2-2 on a stripped proof paragraph is
    equally a statement about the judge and about that email, and the bench
    cannot say which it meant.

    **Deduplicated on the control text, not on the case name**, and that is not
    housekeeping. `rich-sequence` and `rich-single` are two requests against
    one business carrying the *same* control email and the same persona, so the
    set used to yield three sources of which two were one email under two
    names. Every pair on it was bought twice, and the report counted them as
    independent items - manufacturing exactly the confound the rest of this
    file exists to remove, while charging for it.
    """
    candidates: list[BenchSource] = []
    for case in cases:
        if not case.control_email.strip():
            continue
        try:
            email = parse_email(case.control_email, position=1)
        except EmailCopyError as exc:
            logger.warning("bench: control for %s is not sendable (%s)", case.name, exc)
            continue
        persona = case.target_market or "a busy professional who has never heard of this company"
        candidates.append(
            BenchSource(name=case.name, email=email, persona=persona, anchor=True)
        )
    if not anchors_only:
        candidates.extend(bench_only_sources())

    sources: list[BenchSource] = []
    seen: set[str] = set()
    for source in candidates:
        fingerprint = render_email(source.email)
        if fingerprint in seen:
            logger.info(
                "bench: %s carries a control already in the set - not benching it twice",
                source.name,
            )
            continue
        seen.add(fingerprint)
        sources.append(source)
    return sources


def pairs_for(
    sources: list[BenchSource], mutations: tuple[Mutation, ...]
) -> list[tuple[BenchSource, Email, Mutation]]:
    """Every (source, mutant) the bench would judge, built without a model.

    Separate from running them so `--dry-run` can print the mutants for a
    person to read. That check matters more than it looks: the whole bench
    rests on the mutants being plausible worse emails rather than broken ones,
    and that is a judgment only a human eye can make.
    """
    return [
        (source, mutation.apply(source.email), mutation)
        for source in sources
        for mutation in mutations
    ]


async def _inbox_arm(
    scanner: SubjectBakeOff, original: Email, mutant: Email, persona: str
) -> tuple[float, float] | None:
    """Both lines put in an inbox, in both orders.

    Two calls rather than one, for the reason the duel casts an even ballot: a
    list is read top down, and a scanner shown one line above another will
    favour the position unless the pairing is cancelled. Still cheaper than the
    four-vote ballot it replaces.

    The sender is deliberately unnamed. The bench has no compiled knowledge, so
    there is no company name to give - and a scanner told nothing about who
    sent it is judging the line, which is what this arm is for.
    """
    first = SubjectOption(subject=original.subject, preview=original.preview_text)
    second = SubjectOption(subject=mutant.subject, preview=mutant.preview_text)
    forward = await scanner.rank([first, second], "", [persona])
    backward = await scanner.rank([second, first], "", [persona])
    if len(forward) != 2 or len(backward) != 2:
        return None
    return (forward[0] + backward[1]) / 2, (forward[1] + backward[0]) / 2


async def run_bench(
    *,
    judge_session: ModelSession,
    reader_session: ModelSession | None = None,
    sources: list[BenchSource] | None = None,
    mutations: tuple[Mutation, ...] = MUTATIONS,
    votes: int = DEFAULT_VOTES,
) -> BenchReport:
    """Judge every pair. The originals are read once each, not once per pair.

    Damage that lives entirely above the body does not go to the judge at all -
    see `_subject_only`. It goes to the inbox scanner, on the same session,
    because that is the instrument the system actually uses to decide between
    two subject lines.
    """
    sources = sources if sources is not None else bench_sources()
    judge = PreferenceJudge(judge_session)
    scanner = SubjectBakeOff(judge_session)
    reader = BlindReader(reader_session) if reader_session is not None else None
    report = BenchReport(votes_per_pair=votes)

    # Bought once per source rather than once per pair: the original does not
    # change between mutations, and re-reading it would be the single largest
    # avoidable cost in the bench.
    original_pull: dict[str, float] = {}
    if reader is not None:
        for source in sources:
            original_pull[source.name] = (
                await reader.read(source.email, [source.persona])
            ).pull

    def unjudged(source: BenchSource, mutation: Mutation, reason: str) -> PairResult:
        return PairResult(
            source=source.name, mutation=mutation, anchor=source.anchor, skipped=reason
        )

    for source, mutant, mutation in pairs_for(sources, mutations):
        name, original, persona = source.name, source.email, source.persona
        if not mutation.invariant and render_email(mutant) == render_email(original):
            report.pairs.append(
                unjudged(source, mutation, "this email had nothing for it to break")
            )
            continue

        # One pair at a time, because a bench is a hundred-odd billed calls and
        # a single dropped connection two thirds of the way through would
        # otherwise throw away everything bought before it. A pair nobody could
        # judge is recorded as unjudged rather than as a miss - the same rule
        # the reader panel already applies to a read that never came back.
        try:
            if _subject_only(original, mutant):
                ranked = await _inbox_arm(scanner, original, mutant, persona)
                if ranked is None:
                    report.pairs.append(
                        unjudged(source, mutation, "nobody could rank the two subject lines")
                    )
                    continue
                report.pairs.append(
                    PairResult(
                        source=name,
                        mutation=mutation,
                        anchor=source.anchor,
                        original_opens=ranked[0],
                        mutant_opens=ranked[1],
                        gate_issues=tuple(
                            issue.detail for issue in _free_gates(mutant).issues
                        ),
                    )
                )
                continue
            duel = await judge.duel(
                challenger=mutant, champion=original, personas=[persona], votes=votes
            )
            mutant_pull: float | None = None
            if reader is not None:
                mutant_pull = (await reader.read(mutant, [persona])).pull
        except ProviderError as exc:
            logger.warning("bench: %s / %s could not be judged - %s", name, mutation.name, exc)
            report.pairs.append(unjudged(source, mutation, f"the provider failed ({exc})"))
            continue
        if not duel.decided:
            # Every ballot line came back empty. The judge itself absorbs a
            # vote that never arrived - that is what keeps a campaign alive
            # through a blip - so a provider that has stopped answering
            # reaches here as a duel with nothing in either column rather than
            # as an exception. Recorded as unjudged, because 0-0 is not a tie
            # the original failed to win.
            logger.warning(
                "bench: %s / %s - not one vote came back", name, mutation.name
            )
            report.pairs.append(
                unjudged(
                    source,
                    mutation,
                    f"the provider failed ({duel.unreported} vote(s) never came back)",
                )
            )
            continue
        report.pairs.append(
            PairResult(
                source=name,
                mutation=mutation,
                anchor=source.anchor,
                original_votes=duel.champion_votes,
                mutant_votes=duel.challenger_votes,
                unreported=duel.unreported,
                reasons=duel.reasons,
                original_pull=original_pull.get(name) if reader is not None else None,
                mutant_pull=mutant_pull,
                gate_issues=tuple(issue.detail for issue in _free_gates(mutant).issues),
            )
        )
    return report


# --------------------------------------------------------------------- cli


#: Calls one subject-only pair costs: the two lines ranked in both orders. See
#: `_inbox_arm`.
_INBOX_CALLS = 2


def _estimate(
    pair_count: int, votes: int, sources: int, with_reader: bool, inbox_pairs: int = 0
) -> str:
    ballot = max(2, votes + votes % 2)
    calls = (pair_count - inbox_pairs) * ballot + inbox_pairs * _INBOX_CALLS
    if with_reader:
        calls += sources + pair_count
    return f"about {calls} model call(s)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--votes", type=int, default=DEFAULT_VOTES)
    parser.add_argument("--mutation", action="append", help="run one mutation by name (repeatable)")
    parser.add_argument(
        "--hard",
        action="store_true",
        help=(
            "run only the subtle tier. The original six are passed 32/33, so they are a "
            "regression guard now rather than a measurement; these four still have room"
        ),
    )
    parser.add_argument(
        "--case", action="append", help="run one control by name (repeatable)"
    )
    parser.add_argument(
        "--anchors-only",
        action="store_true",
        help=(
            "bench only the controls a person wrote. Cheap, and the honest fallback if the "
            "fixtures in controls.py are ever suspected of being easy"
        ),
    )
    parser.add_argument(
        "--with-reader",
        action="store_true",
        help="also score both sides with the blind reader (one extra call per pair)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the pairs and spend nothing - use it to check the mutants read as plausible",
    )
    parser.add_argument("--out", type=Path, help="write the report here as well as to stdout")
    parser.add_argument(
        "--judge-model",
        choices=[model.value for model in ClaudeModel],
        help="bench a specific model instead of whatever the roles resolve to today",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)

    # A rendered email carries "→" and this report carries ✓/✗, none of which
    # survive a cp1252 console. Without this the bench dies on its own output
    # on Windows, after the model calls have already been paid for.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    sources = bench_sources(anchors_only=args.anchors_only)
    if args.case:
        wanted = set(args.case)
        sources = [source for source in sources if source.name in wanted]
    if not sources:
        parser.error(
            f"no control email to mutate in that selection. Have: "
            f"{', '.join(source.name for source in bench_sources())}"
        )

    mutations = HARD_MUTATIONS if args.hard else MUTATIONS
    if args.mutation:
        chosen = [mutation_named(name) for name in args.mutation]
        missing = [name for name, found in zip(args.mutation, chosen, strict=True) if found is None]
        if missing:
            parser.error(
                f"no mutation named {missing} - "
                f"have: {', '.join(item.name for item in MUTATIONS)}"
            )
        mutations = tuple(item for item in chosen if item is not None)

    pairs = pairs_for(sources, mutations)
    inbox_pairs = sum(
        1
        for source, mutant, mutation in pairs
        if not mutation.invariant and _subject_only(source.email, mutant)
    )

    if args.dry_run:
        for source, mutant, mutation in pairs:
            name, original = source.name, source.email
            unchanged = render_email(mutant) == render_email(original)
            origin = "written by a person" if source.anchor else "written for the bench"
            print(
                f"\n{'=' * 70}\n{name} ({origin}) · {mutation.name}"
                f"\n  breaks: {mutation.breaks}"
            )
            if unchanged and not mutation.invariant:
                print("  !! no-op on this email - the bench will skip this pair")
            elif not mutation.invariant and _subject_only(original, mutant):
                print("  -> identical below the subject: ranked in an inbox, not duelled")
            print(f"{'-' * 70}\n{render_email(mutant)}")
        print(
            f"\n{len(pairs)} pair(s). Running for real would cost "
            f"{_estimate(len(pairs), args.votes, len(sources), args.with_reader, inbox_pairs)}."
        )
        return 0

    print(
        f"Benching the judges on {len(pairs)} pair(s) against REAL models "
        f"({_estimate(len(pairs), args.votes, len(sources), args.with_reader, inbox_pairs)}).\n"
        "This spends quota.",
        flush=True,
    )

    model = args.judge_model or DEFAULT_JUDGE_MODEL

    def session(execution: str) -> ModelSession:
        return ModelSession(
            provider=get_ai_provider(),
            prompt_engine=get_prompt_engine(PROMPTS_DIR),
            events=EventBus(),
            # No override unless one was asked for, so the roles resolve
            # through the tier map exactly as they do inside a campaign.
            model_router=ModelRouter({"*": model} if model else None),
            execution_id=execution,
        )

    report = asyncio.run(
        run_bench(
            judge_session=session("bench-judge"),
            reader_session=session("bench-reader") if args.with_reader else None,
            sources=sources,
            mutations=mutations,
            votes=args.votes,
        )
    )
    rendered = report.render()
    print(f"\n{rendered}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
