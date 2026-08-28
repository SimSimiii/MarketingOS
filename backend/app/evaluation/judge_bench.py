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
import sys
from dataclasses import dataclass, field
from pathlib import Path

from app.ai.factory import get_ai_provider
from app.ai.model_router import ModelRouter
from app.ai.models import ClaudeModel
from app.core.config import PROMPTS_DIR
from app.evaluation.golden import GOLDEN_CASES, GoldenCase
from app.evaluation.mutations import MUTATIONS, Mutation, mutation_named
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
            return f"  · {self.mutation.name:<24} {self.source:<14} skipped - {self.skipped}"
        if self.mutation.invariant:
            verdict = "even" if self.lean == 0 else f"leans {self.lean}"
        else:
            verdict = "caught" if self.caught else "MISSED"
        mark = "·" if self.mutation.invariant else ("✓" if self.caught else "✗")
        # An inbox pair has no ballot, so the column that holds one says what
        # was asked instead - printing 0-0 there would read as a duel nobody
        # could judge, which is a different result entirely.
        tally = "in inbox" if self.by_inbox else f"{self.original_votes}-{self.mutant_votes}"
        line = f"  {mark} {self.mutation.name:<24} {self.source:<14} {tally:<8}  {verdict}"
        if self.by_inbox:
            line += f"   opens {self.original_opens:.0f} vs {self.mutant_opens:.0f} in 100"
        if self.original_pull is not None and self.mutant_pull is not None:
            line += f"   pull {self.original_pull:.0f} → {self.mutant_pull:.0f}"
        if self.gate_issues:
            line += f"   gates: {len(self.gate_issues)}"
        if self.unreported:
            line += f"   ({self.unreported} vote(s) did not come back)"
        return line


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
    def noise(self) -> float:
        """Average distance from an even split on pairs that are not damaged.

        Zero is a judge reading the copy. The ballot already alternates label
        order, so anything much above zero is the instrument answering from
        something other than what is on the page.
        """
        pairs = self.invariants
        return sum(pair.lean for pair in pairs) / len(pairs) if pairs else 0.0

    def render(self) -> str:
        lines = [
            (
                f"Judge bench - {len({pair.source for pair in self.pairs})} source email(s), "
                f"{len(self.pairs)} pair(s), {self.votes_per_pair} votes each"
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

        lines.append("\nDetection")
        lines.append(
            f"  judgment-only   {sum(1 for p in self.judgment_only if p.caught)}"
            f"/{len(self.judgment_only)} ({self.detection_rate:.0%})   <- the number that matters"
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
            splits = ", ".join(f"{p.original_votes}-{p.mutant_votes}" for p in self.invariants)
            lines.append(
                f"\nNoise floor\n  undamaged pairs split {splits} "
                f"(average lean {self.noise:.1f}; 0 is a judge reading the copy)"
            )
        return "\n".join(lines)


# --------------------------------------------------------------------- run


def bench_sources(cases: tuple[GoldenCase, ...] = GOLDEN_CASES) -> list[tuple[str, Email, str]]:
    """The originals, and who reads them.

    Reused from the golden set rather than written fresh: those controls are
    already documented as what a competent freelancer sends on a Tuesday, they
    are already held inline so they cannot drift, and a bench whose "good"
    email is one the author wrote for the bench is a bench that proves the
    author's taste.
    """
    sources: list[tuple[str, Email, str]] = []
    for case in cases:
        if not case.control_email.strip():
            continue
        try:
            email = parse_email(case.control_email, position=1)
        except EmailCopyError as exc:
            logger.warning("bench: control for %s is not sendable (%s)", case.name, exc)
            continue
        persona = case.target_market or "a busy professional who has never heard of this company"
        sources.append((case.name, email, persona))
    return sources


def pairs_for(
    sources: list[tuple[str, Email, str]], mutations: tuple[Mutation, ...]
) -> list[tuple[str, Email, Email, str, Mutation]]:
    """Every (original, mutant) the bench would judge, built without a model.

    Separate from running them so `--dry-run` can print the mutants for a
    person to read. That check matters more than it looks: the whole bench
    rests on the mutants being plausible worse emails rather than broken ones,
    and that is a judgment only a human eye can make.
    """
    built: list[tuple[str, Email, Email, str, Mutation]] = []
    for name, original, persona in sources:
        for mutation in mutations:
            built.append((name, original, mutation.apply(original), persona, mutation))
    return built


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
    sources: list[tuple[str, Email, str]] | None = None,
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
        for name, original, persona in sources:
            original_pull[name] = (await reader.read(original, [persona])).pull

    def unjudged(name: str, mutation: Mutation, reason: str) -> PairResult:
        return PairResult(source=name, mutation=mutation, skipped=reason)

    for name, original, mutant, persona, mutation in pairs_for(sources, mutations):
        if not mutation.invariant and render_email(mutant) == render_email(original):
            report.pairs.append(unjudged(name, mutation, "this email had nothing for it to break"))
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
                        unjudged(name, mutation, "nobody could rank the two subject lines")
                    )
                    continue
                report.pairs.append(
                    PairResult(
                        source=name,
                        mutation=mutation,
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
            report.pairs.append(unjudged(name, mutation, f"the provider failed ({exc})"))
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
                    name,
                    mutation,
                    f"the provider failed ({duel.unreported} vote(s) never came back)",
                )
            )
            continue
        report.pairs.append(
            PairResult(
                source=name,
                mutation=mutation,
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
    parser.add_argument("--case", action="append", help="run one golden case by name (repeatable)")
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

    cases = GOLDEN_CASES
    if args.case:
        cases = tuple(case for case in GOLDEN_CASES if case.name in set(args.case))
        if not cases:
            parser.error(f"no golden case named any of {args.case}")
    sources = bench_sources(cases)
    if not sources:
        parser.error("no golden case in that selection has a control email to mutate")

    mutations = MUTATIONS
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
        for _, original, mutant, _, mutation in pairs
        if not mutation.invariant and _subject_only(original, mutant)
    )

    if args.dry_run:
        for name, original, mutant, _, mutation in pairs:
            unchanged = render_email(mutant) == render_email(original)
            print(f"\n{'=' * 70}\n{name} · {mutation.name}\n  breaks: {mutation.breaks}")
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
