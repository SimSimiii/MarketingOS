"""Experiment 1: does better audience intelligence change what the system makes?

    python -m app.evaluation.audience_bench --case rich-single --dry-run
    python -m app.evaluation.audience_bench --case rich-single --out eval/audience
    python -m app.evaluation.audience_bench --report eval/audience

Three runs of one golden case, identical in every respect except what the
campaign knows about its buyer: nothing, a demand map of the kind the shipped
cartographer produces, and a hand-written record standing in for what a
grounded research stage could ideally provide. See `app.evaluation.audience`
for the arms themselves and for the two things held constant inside them.

**This is billed, and it is three campaigns per case rather than one.** The
dry run costs nothing and prints what each arm would be pointed at, which is
worth reading first: a fixture that does not say anything the other arm's
fixture does not is an experiment that cannot come back with an answer.

What the report is for
----------------------

The table's first block is quality - the votes against a human-written control,
the pull, what shipped. The second block is validity, and it is the one to read
first: it says which of the fixture's own sentences turned up in which role's
prompt. An arm whose markers reached nothing did not run the experiment,
whatever its numbers say, and a comparison between two arms that both reached
nothing is a measurement of run-to-run noise wearing an experiment's clothes.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from app.evaluation.audience import (
    CONDITIONS,
    SHARED,
    AudienceCondition,
    arm_for,
    cases_with_fixtures,
)
from app.evaluation.golden import GoldenCase, case_named
from app.evaluation.head_to_head import VOTES
from app.evaluation.record import RunRecord
from app.evaluation.runner import run_case
from app.evaluation.scaffold import PROBED_ROLES, describe
from app.marketing.contract import parse_contract
from app.marketing.forecast import forecast
from app.marketing.policy import PolicyPreset, resolve_policy

logger = logging.getLogger("marketingos.evaluation")

#: Width of one arm's column. Wide enough for a truncated segment name, narrow
#: enough that three arms and a row label fit an eighty-column terminal.
_COLUMN = 24
_LABEL = 28


def record_path(out: Path, case: str, condition: str) -> Path:
    """One file per arm, so a re-run of one arm does not disturb the others."""
    return out / f"{case}.{condition}.json"


# ------------------------------------------------------------------ running


async def run_experiment(
    case: GoldenCase,
    preset: PolicyPreset,
    conditions: tuple[AudienceCondition, ...],
    out: Path,
) -> dict[str, RunRecord]:
    out.mkdir(parents=True, exist_ok=True)
    records: dict[str, RunRecord] = {}
    for condition in conditions:
        print(f"\n=== {case.name} [{preset}] · audience: {condition} ===", flush=True)
        try:
            record = await run_case(case, preset, condition)
        # One arm failing must not cost the arms that already ran: they are
        # written to disk as they finish, and a two-arm comparison is worth
        # more than nothing at all.
        except Exception as exc:
            logger.exception("arm %s of %s failed", condition, case.name)
            print(f"  !! {case.name} [{condition}] failed: {exc}", flush=True)
            continue
        record_path(out, case.name, str(condition)).write_text(
            record.model_dump_json(indent=2), encoding="utf-8"
        )
        records[str(condition)] = record
        print(f"  {record.summary()}", flush=True)
    return records


# ---------------------------------------------------------------- reporting


def _load(directory: Path) -> dict[str, dict[str, RunRecord]]:
    """Every arm on disk, grouped by case then by condition."""
    found: dict[str, dict[str, RunRecord]] = {}
    for path in sorted(directory.glob("*.json")):
        record = RunRecord.model_validate_json(path.read_text(encoding="utf-8"))
        condition = record.audience_condition or "unlabelled"
        found.setdefault(record.case, {})[condition] = record
    return found


def _cell(value: str) -> str:
    text = value if value else "-"
    if len(text) > _COLUMN - 2:
        text = text[: _COLUMN - 3] + "…"
    return text.ljust(_COLUMN)


def _row(label: str, values: list[str]) -> str:
    return "  " + label.ljust(_LABEL) + "".join(_cell(value) for value in values)


def _verdict(record: RunRecord) -> str:
    if record.control_note:
        return record.control_note
    if not (record.control_votes_for + record.control_votes_against):
        return "nobody could choose"
    if record.control_votes_for > record.control_votes_against:
        return "beats the human"
    if record.control_votes_for == record.control_votes_against:
        return "level with the human"
    return "loses to the human"


def _bodies(record: RunRecord) -> tuple[str, ...]:
    return tuple(email.email.body if email.email else "" for email in record.emails)


def _first(record: RunRecord, field: str) -> str:
    return getattr(record.emails[0], field, "") if record.emails else ""


def _reached(record: RunRecord, role: str) -> str:
    labels = record.audience_reached.get(role)
    if labels is None:
        return "not probed"
    return (
        ", ".join(
            label.split(".", 1)[-1] + ("*" if label.startswith(f"{SHARED}.") else "")
            for label in labels
        )
        or "nothing"
    )


def _conditions_present(arms: dict[str, RunRecord]) -> list[str]:
    """Arms in the canonical order, then anything unexpected, so a report of a
    partial round still shows the columns it does have."""
    known = [str(condition) for condition in CONDITIONS if str(condition) in arms]
    return known + sorted(set(arms) - set(known))


def render_case(case: str, arms: dict[str, RunRecord]) -> str:
    order = _conditions_present(arms)
    records = [arms[name] for name in order]
    preset = records[0].preset if records else ""
    lines = [
        f"Golden Case: {case}   [{preset} preset]",
        "",
        "  " + "".ljust(_LABEL) + "".join(_cell(name.upper()) for name in order),
        "  " + "-" * (_LABEL + _COLUMN * len(order)),
        _row("status", [record.run_status for record in records]),
        _row("segment chosen", [record.audience_segment for record in records]),
        _row(
            "reader persona",
            [
                record.reader_personas[0] if record.reader_personas else ""
                for record in records
            ],
        ),
        "",
        _row(
            "control votes (for-against)",
            [
                f"{record.control_votes_for}-{record.control_votes_against}"
                for record in records
            ],
        ),
        _row("vs. the human", [_verdict(record) for record in records]),
        _row("avg pull", [f"{record.average_pull:.1f}" for record in records]),
        _row("landed rate", [f"{record.landed_rate:.0%}" for record in records]),
        _row(
            "revisions (total)",
            [str(sum(email.rewrites for email in record.emails)) for record in records],
        ),
        _row(
            "first-draft ships",
            [f"{record.first_draft_ship_rate:.0%}" for record in records],
        ),
        _row(
            "proof on the page",
            [f"{record.substantiation_rate:.0%}" for record in records],
        ),
        _row(
            "gate failures left",
            [
                str(sum(len(email.unresolved) for email in record.emails))
                for record in records
            ],
        ),
        _row("repairs", [str(record.repairs) for record in records]),
        "",
        _row("winning idea (email 1)", [_first(record, "idea") for record in records]),
        _row("subject (email 1)", [_first(record, "subject") for record in records]),
        _row(
            "same copy as first arm",
            ["-"]
            + [
                "yes" if _bodies(record) == _bodies(records[0]) else "no"
                for record in records[1:]
            ],
        ),
        "",
        _row("model calls", [str(record.model_calls) for record in records]),
        _row("cost", [f"${record.cost_usd:.2f}" for record in records]),
        "",
        (
            "  Audience reaching each role (fixture phrases found in its prompts; "
            "* = carried by both arms)"
        ),
    ]
    lines.extend(
        _row(f"  {role}", [_reached(record, role) for record in records])
        for role in PROBED_ROLES
    )
    lines.extend(["", *_validity(order, records)])
    return "\n".join(lines)


def _validity(order: list[str], records: list[RunRecord]) -> list[str]:
    """Whether the experiment was an experiment.

    Printed under every table rather than left to the reader, because the
    failure it names is invisible in the numbers: three arms that all reached
    nothing produce three different sets of results, because the pipeline is
    stochastic, and a reader looking only at pull would read that noise as an
    effect.
    """
    notes: list[str] = ["  Validity"]
    for name, record in zip(order, records, strict=True):
        found = {label for labels in record.audience_reached.values() for label in labels}
        mine = {label for label in found if label.startswith(f"{name}.")}
        # A phrase both informed arms carry says an audience record arrived and
        # nothing about which one, so it counts for neither and is not foreign.
        shared = {label for label in found if label.startswith(f"{SHARED}.")}
        foreign = found - mine - shared
        if name == str(AudienceCondition.NONE):
            notes.append(
                "    ok   none: no fixture phrase reached any role"
                if not found
                else f"    FAIL none: {sorted(found)} reached a role - this arm is not a control"
            )
            continue
        if not record.audience_reached:
            notes.append(f"    ??   {name}: nothing was probed - record written before the probe")
        elif not mine:
            notes.append(
                f"    FAIL {name}: not one of its own phrases reached any role. The arm did "
                "not change the run, so its numbers are noise."
            )
        else:
            notes.append(
                f"    ok   {name}: {len(mine)} of its phrases reached "
                f"{sum(1 for labels in record.audience_reached.values() if labels)} role(s)"
                + (f"; also saw {sorted(foreign)}" if foreign else "")
            )
    personas = {tuple(record.reader_personas) for record in records}
    if len(personas) < len(records):
        notes.append(
            "    FAIL two or more arms were graded by identical cold readers - the audience "
            "did not reach the instrument that decides what ships"
        )
    notes.extend(
        [
            (
                "    note the arms share one segment and one fit, so this cannot say "
                "whether a researched stage would pick a better buyer - only whether "
                "knowing this one better changes the copy."
            ),
            (
                "    note the human control was written for the buyer on the company's own "
                "homepage, and the informed arms are aimed somewhere else. The control "
                "votes therefore carry an audience mismatch as well as a quality "
                "difference; the rows above it do not."
            ),
            (
                "    note one round per arm. Every writer, reader and judge call is "
                "sampled, so a single three-arm table cannot separate the condition from "
                "run-to-run variance - re-run an arm into a second directory before "
                "believing a small gap."
            ),
        ]
    )
    return notes


def report(directory: Path) -> None:
    cases = _load(directory)
    if not cases:
        print(f"No records in {directory}.")
        return
    for case, arms in cases.items():
        print(f"\n{render_case(case, arms)}")


# --------------------------------------------------------------------- cli


def _estimate(cases: tuple[GoldenCase, ...], preset: PolicyPreset, arms: int) -> str:
    policy = resolve_policy(preset)
    low = high = 0
    for case in cases:
        material = sum(len(content) for _, content in case.documents)
        shape = forecast(policy, parse_contract(case.request), material)
        low += shape.low + (VOTES if case.control_email else 0)
        high += shape.high + (VOTES if case.control_email else 0)
    return f"about {low * arms}-{high * arms} model call(s)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case", action="append", help="one golden case by name (repeatable)"
    )
    parser.add_argument(
        "--arm",
        action="append",
        choices=[str(condition) for condition in CONDITIONS],
        help="one audience condition (repeatable); all three by default",
    )
    parser.add_argument(
        "--preset", default="balanced", choices=["fast", "balanced", "maximum"]
    )
    parser.add_argument("--out", type=Path, help="directory to write records to")
    parser.add_argument(
        "--report", type=Path, help="render a finished round instead of running anything"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print what each arm would be pointed at, and spend nothing",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)

    # The tables are drawn with "·" and "…", neither of which survives a cp1252
    # console - see runner.py, where this cost a paid-for round its output.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if args.report:
        report(args.report)
        return 0

    names = args.case or list(cases_with_fixtures())
    cases: list[GoldenCase] = []
    for name in names:
        found = case_named(name)
        if found is None:
            parser.error(f"no golden case named {name!r}")
        if name not in cases_with_fixtures():
            parser.error(
                f"golden case {name!r} has no hand-written audience arms - "
                f"have: {', '.join(cases_with_fixtures())}"
            )
        cases.append(found)
    conditions = (
        tuple(AudienceCondition(name) for name in args.arm) if args.arm else CONDITIONS
    )

    if args.dry_run:
        for case in cases:
            print(f"\n{'=' * 70}\n{case.name}: {case.request}")
            for condition in conditions:
                arm = arm_for(case.name, condition)
                print(f"\n--- arm: {condition} ---\n  {describe(arm)}\n")
                print(arm.render() if arm is not None else "  (no fixture)")
        print(
            f"\n{len(cases)} case(s) x {len(conditions)} arm(s). Running for real would "
            f"cost {_estimate(tuple(cases), args.preset, len(conditions))}."
        )
        return 0

    if args.out is None:
        parser.error("--out is required when running arms")

    print(
        f"Running {len(cases)} case(s) x {len(conditions)} audience arm(s) on the "
        f"{args.preset} preset against REAL models "
        f"({_estimate(tuple(cases), args.preset, len(conditions))}).\n"
        "This spends quota.",
        flush=True,
    )
    for case in cases:
        asyncio.run(run_experiment(case, args.preset, conditions, args.out))
    report(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
