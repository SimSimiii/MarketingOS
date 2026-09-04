"""Experiment 2: does the persona change which draft the cold reader prefers?

    python -m app.evaluation.persona_bench --case rich-single --dry-run
    python -m app.evaluation.persona_bench --case rich-single --out eval/persona
    python -m app.evaluation.persona_bench --case rich-single --drafts eval/audience

The cheap half of the audience question. Experiment 1 rewrites the campaign
under each condition and therefore pays for a whole run per arm; this one holds
the **emails fixed** and changes only who reads them. Nothing is written, no
rewrite is bought, and the only calls are cold reads.

It answers a narrower question, and the narrowness is the point: the blind
reader is the instrument every other decision in the craft loop is read off -
which candidate survives the bake-off, whether a rewrite helped, whether a draft
ships. If a better persona does not change that instrument's ordering of a fixed
set of drafts, then a better persona cannot change what the loop selects, and
the whole audience-research investment would have to earn itself somewhere else.

**This measures sensitivity, not marketing performance.** A ranking that changes
says the instrument is persona-sensitive. It does not say the researched
persona's ranking is the right one - nobody has sent these emails, there is no
outcome to check either ordering against, and a richer fixture being *different*
is not evidence of it being *correct*. The report says so on its own last line,
because that is the sentence a reader of a table like this most wants to skip.
"""

import argparse
import asyncio
import hashlib
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

from app.ai.factory import get_ai_provider
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR
from app.evaluation.audience import AudienceCondition, persona_conditions
from app.evaluation.golden import GoldenCase, case_named
from app.evaluation.mutations import mutation_named
from app.evaluation.record import RunRecord
from app.knowledge.artifacts import AudienceModel
from app.market.demand import AudienceSegment
from app.marketing.email_copy import Email, EmailCopyError, parse_email, render_email
from app.marketing.reader import BlindReader, PanelRead, personas_for
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import get_prompt_engine

logger = logging.getLogger("marketingos.evaluation")

#: The built-in draft set, when no finished round is handed in. The case's
#: human-written control plus three of it damaged in ways whose direction is
#: not a matter of opinion - see `app.evaluation.mutations`.
#:
#: Only judgment-visible mutations: a mutant a deterministic gate would have
#: caught tells us nothing about a reader, and this experiment never runs the
#: gates. They are here to be *different same-product emails a reader can rank*,
#: not to be a hidden answer key: the question is whether two personas order
#: them differently, and that question is well posed however good the drafts
#: are, as long as both personas see the same ones.
_BUILT_IN_MUTATIONS = ("specifics_to_adjectives", "open_on_the_company", "hedge_the_claims")

_COLUMN = 26
_LABEL = 30


@dataclass(frozen=True)
class DraftSet:
    """The emails both personas read. Fixed by construction."""

    case: str
    origin: str
    #: (label, email), in the order they will be reported.
    drafts: tuple[tuple[str, Email], ...] = ()

    @property
    def fingerprint(self) -> str:
        """Identity of the copy, so the report can prove nothing was rewritten
        between conditions rather than asserting it."""
        rendered = "\n".join(render_email(email) for _, email in self.drafts)
        return hashlib.sha256(rendered.encode("utf-8")).hexdigest()[:12]


@dataclass
class PersonaArm:
    """One persona's reading of the whole draft set."""

    condition: str
    personas: tuple[str, ...] = ()
    reads: dict[str, PanelRead] = field(default_factory=dict)
    #: The exact text each draft was shown as, hashed. Compared across arms:
    #: an experiment that quietly re-rendered the drafts between conditions is
    #: not the experiment this file claims to run.
    shown: str = ""

    def ordered(self, labels: tuple[str, ...]) -> list[str]:
        """The drafts best first, by the comparison the craft loop uses.

        Comprehension first and then pull, exactly as `EmailVersion.measured`
        orders two candidates - minus the gates and the substantiation, neither
        of which this experiment varies, because both are properties of the
        copy and the copy is held fixed. Ties keep the order the drafts arrived
        in, so a persona that separates nothing reports the input order rather
        than an arbitrary one.
        """
        return sorted(
            labels,
            key=lambda label: (
                -int(self.reads[label].understood),
                -self.reads[label].pull,
                labels.index(label),
            ),
        )

    def rank_of(self, label: str, labels: tuple[str, ...]) -> int:
        return self.ordered(labels).index(label) + 1

    def winner(self, labels: tuple[str, ...]) -> str:
        return self.ordered(labels)[0] if labels else ""


# ------------------------------------------------------------- draft sets


def built_in_drafts(case: GoldenCase) -> DraftSet:
    """The case's control, and three plausible worse versions of it."""
    control = parse_email(case.control_email, position=1)
    drafts: list[tuple[str, Email]] = [("control", control)]
    for name in _BUILT_IN_MUTATIONS:
        mutation = mutation_named(name)
        if mutation is None:
            continue
        mutant = mutation.apply(control)
        if render_email(mutant) == render_email(control):
            # A mutation with nothing to bite on in this email. Two identical
            # drafts in one set makes every ranking difference a coin toss.
            logger.info("persona bench: %s is a no-op on this control - dropped", name)
            continue
        drafts.append((name, mutant))
    return DraftSet(
        case=case.name,
        origin=f"the golden control plus {len(drafts) - 1} mutant(s)",
        drafts=tuple(drafts),
    )


def drafts_from_records(directory: Path, case: str) -> DraftSet:
    """The emails a finished round actually delivered.

    An `audience_bench` output directory is the natural input: it holds the
    same case's copy as written under each audience condition, which makes this
    experiment ask whether a reader who knows the buyer ranks those three the
    way the runs that produced them did.
    """
    paths = sorted(directory.glob("*.json")) if directory.is_dir() else [directory]
    drafts: list[tuple[str, Email]] = []
    for path in paths:
        record = RunRecord.model_validate_json(path.read_text(encoding="utf-8"))
        if record.case != case:
            continue
        arm = record.audience_condition or "run"
        for email in record.emails:
            if email.email is None:
                # Written before records carried the copy. Nothing to read.
                continue
            drafts.append((f"{arm}:email{email.position}", email.email))
    return DraftSet(case=case, origin=str(directory), drafts=tuple(drafts))


# ------------------------------------------------------------------ running


def panel_for(segment: AudienceSegment, panel: bool = True) -> list[str]:
    """The cold readers one segment produces, through production's own function.

    `personas_for` is what the craft loop calls, and it reads exactly two
    fields off a segment - the name and the situation. That is a finding rather
    than an inconvenience, and it is why the researched fixtures put their
    detail in `who`: whatever else a future research stage learns, this is the
    aperture it currently has to fit through to reach the instrument that
    decides what ships.
    """
    as_segment = segment.as_segment()
    return personas_for(AudienceModel(segments=[as_segment]), as_segment, panel=panel)


async def read_all(
    reader: BlindReader, drafts: DraftSet, personas: list[str]
) -> dict[str, PanelRead]:
    """Every draft in the set, read by one persona's panel."""
    reads: dict[str, PanelRead] = {}
    for label, email in drafts.drafts:
        reads[label] = await reader.read(email, personas)
    return reads


async def run_persona_bench(
    reader: BlindReader,
    drafts: DraftSet,
    segments: dict[AudienceCondition, AudienceSegment],
    panel: bool = True,
) -> list[PersonaArm]:
    """The same drafts, under each persona in turn.

    The draft objects are the identical instances in both arms - not copies,
    not re-parsed - which is what makes "only the persona changed" a property of
    the code rather than a claim in a docstring. `shown` records what was put
    in front of the reader so the report can show the two arms agree.
    """
    arms: list[PersonaArm] = []
    for condition, segment in segments.items():
        personas = panel_for(segment, panel=panel)
        print(f"  · reading as {condition}: {personas[0][:70]}", flush=True)
        reads = await read_all(reader, drafts, personas)
        arms.append(
            PersonaArm(
                condition=str(condition),
                personas=tuple(personas),
                reads=reads,
                shown=drafts.fingerprint,
            )
        )
    return arms


# ---------------------------------------------------------------- reporting


def _cell(value: str) -> str:
    text = value or "-"
    if len(text) > _COLUMN - 2:
        text = text[: _COLUMN - 3] + "…"
    return text.ljust(_COLUMN)


def _row(label: str, values: list[str]) -> str:
    return "  " + label.ljust(_LABEL) + "".join(_cell(value) for value in values)


def render(drafts: DraftSet, arms: list[PersonaArm]) -> str:
    labels = tuple(label for label, _ in drafts.drafts)
    same = len({arm.shown for arm in arms}) == 1
    lines = [
        f"Draft set: {drafts.case}  ({drafts.origin}, {len(labels)} draft(s))",
        (
            f"Identical copy under every persona: {'yes' if same else 'NO - INVALID'} "
            f"[{drafts.fingerprint}]"
        ),
        "",
        "  " + "".ljust(_LABEL) + "".join(_cell(arm.condition.upper()) for arm in arms),
        "  " + "-" * (_LABEL + _COLUMN * len(arms)),
        _row("persona", [arm.personas[0] if arm.personas else "" for arm in arms]),
        "",
    ]
    for label in labels:
        lines.append(_row(f"{label}  rank", [str(arm.rank_of(label, labels)) for arm in arms]))
        lines.append(_row("  pull (panel median)", [f"{arm.reads[label].pull:.1f}" for arm in arms]))
        lines.append(
            _row("  clicks in 100", [f"{arm.reads[label].clicks_in_100:.0f}" for arm in arms])
        )
        lines.append(
            _row("  landed", ["yes" if arm.reads[label].landed else "no" for arm in arms])
        )
        lines.append(
            _row("  understood", ["yes" if arm.reads[label].understood else "no" for arm in arms])
        )
        lines.append(
            _row(
                "  panel verdict",
                [arm.reads[label].verdict_line() for arm in arms],
            )
        )
        lines.append("")
    lines.append(_row("winner", [arm.winner(labels) for arm in arms]))
    lines.append(_row("ranking", [" > ".join(arm.ordered(labels)) for arm in arms]))

    orderings = {tuple(arm.ordered(labels)) for arm in arms}
    winners = {arm.winner(labels) for arm in arms}
    lines.extend(
        [
            "",
            "  Result",
            f"    winner changed with the persona: {'YES' if len(winners) > 1 else 'no'}",
            f"    ranking changed with the persona: {'YES' if len(orderings) > 1 else 'no'}",
            (
                "    this measures sensitivity, not performance - a persona that reorders "
                "the drafts"
            ),
            "    is not thereby the correct one, and nothing here has been sent to anybody.",
        ]
    )
    return "\n".join(lines)


# --------------------------------------------------------------------- cli


def _estimate(drafts: int, arms: int, panel: bool) -> str:
    return f"about {drafts * arms * (3 if panel else 1)} model call(s)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, help="the golden case these drafts are for")
    parser.add_argument(
        "--drafts",
        type=Path,
        help="a finished round's directory (or one record) to take the drafts from; "
        "without it, the case's control email and three mutants of it are used",
    )
    parser.add_argument(
        "--no-panel",
        action="store_true",
        help="one cold reader per draft instead of the panel of three the balanced "
        "preset buys - a third of the cost and a noisier answer",
    )
    parser.add_argument("--out", type=Path, help="write the report here as well as to stdout")
    parser.add_argument(
        "--dry-run", action="store_true", help="print the drafts and personas, spend nothing"
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    case = case_named(args.case)
    if case is None:
        parser.error(f"no golden case named {args.case!r}")
    segments = persona_conditions(case.name)
    if len(segments) < 2:
        parser.error(
            f"golden case {case.name!r} has no hand-written persona pair - "
            "see app.evaluation.audience"
        )

    if args.drafts is not None:
        drafts = drafts_from_records(args.drafts, case.name)
        if not drafts.drafts:
            parser.error(
                f"no drafts for {case.name!r} in {args.drafts} - a round written before "
                "records carried the copy has nothing to re-read"
            )
    else:
        if not case.control_email:
            parser.error(f"golden case {case.name!r} has no control email to build drafts from")
        try:
            drafts = built_in_drafts(case)
        except EmailCopyError as exc:
            parser.error(f"the control email for {case.name!r} is not sendable ({exc})")

    panel = not args.no_panel
    if args.dry_run:
        for condition, segment in segments.items():
            print(f"\n--- persona: {condition} ---")
            for persona in panel_for(segment, panel=panel):
                print(f"  - {persona}")
        for label, email in drafts.drafts:
            print(f"\n{'=' * 70}\n{label}\n{'-' * 70}\n{render_email(email)}")
        print(
            f"\n{len(drafts.drafts)} draft(s) x {len(segments)} persona(s). Running for real "
            f"would cost {_estimate(len(drafts.drafts), len(segments), panel)}."
        )
        return 0

    print(
        f"Reading {len(drafts.drafts)} fixed draft(s) as {len(segments)} persona(s) against "
        f"REAL models ({_estimate(len(drafts.drafts), len(segments), panel)}).\n"
        "This spends quota.",
        flush=True,
    )
    reader = BlindReader(
        ModelSession(
            provider=get_ai_provider(),
            prompt_engine=get_prompt_engine(PROMPTS_DIR),
            events=EventBus(),
            # No override: the reader resolves through the tier map exactly as
            # it does inside a campaign, which is the instrument in question.
            model_router=ModelRouter(None),
            execution_id=f"persona-bench-{case.name}",
        )
    )
    arms = asyncio.run(run_persona_bench(reader, drafts, segments, panel=panel))
    rendered = render(drafts, arms)
    print(f"\n{rendered}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
