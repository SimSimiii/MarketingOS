"""Run the golden set and write down what came back.

    python -m app.evaluation.runner --preset balanced --out eval/2026-08-13
    python -m app.evaluation.runner --compare eval/before eval/after

This spends real money on real models - that is the point, it is the only way
to find out whether a change made the copy better. Nothing here touches the
application database: each case gets a temporary SQLite file that is thrown
away, so a benchmark never leaves campaigns in the user's workspace.
"""

import argparse
import asyncio
import logging
import sys
import tempfile
import time
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.ai.factory import get_ai_provider
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR
from app.evaluation.golden import GOLDEN_CASES, GoldenCase, case_named
from app.evaluation.record import RunRecord, record_from
from app.marketing.observer import RunObserver
from app.marketing.pipeline import EmailCampaignPipeline
from app.marketing.policy import PolicyPreset, resolve_policy
from app.marketing.request import CampaignRequest
from app.models.campaign import Campaign
from app.models.knowledge_document import KnowledgeDocument
from app.orchestration.campaign_orchestrator import _DbKnowledgeGateway
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import get_prompt_engine

logger = logging.getLogger("marketingos.evaluation")


class _RepairCounter(RunObserver):
    """Counts what the run had to redo. A repair is a full writer call whose
    only product is the same email again, and it is invisible in the output."""

    def __init__(self) -> None:
        self.repairs = 0
        self.reasons: list[str] = []

    def on_repair(self, position: int, repair: int, reason: str) -> None:
        self.repairs += 1
        self.reasons.append(f"email {position}: {reason}")

    def on_phase(self, phase: str, message: str, data=None) -> None:
        print(f"    · {message}", flush=True)

    def on_role_started(self, role_id: str, label: str, data=None) -> None:
        print(f"  → {role_id}: {label}", flush=True)


async def run_case(case: GoldenCase, preset: PolicyPreset) -> RunRecord:
    """One golden case, through the real pipeline, against real models."""
    with tempfile.TemporaryDirectory() as workspace:
        engine = create_engine(f"sqlite:///{Path(workspace) / 'eval.db'}")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            campaign = Campaign(
                name=f"[eval] {case.name}",
                request=case.request,
                product_description=case.product_description,
                target_market=case.target_market,
                goals=case.goals,
                policy={"preset": preset},
            )
            session.add(campaign)
            session.commit()
            session.refresh(campaign)
            for title, content in case.documents:
                session.add(
                    KnowledgeDocument(
                        campaign_id=campaign.id,
                        title=title,
                        source_type="markdown",
                        content=content,
                    )
                )
            session.commit()

            policy = resolve_policy(preset)
            observer = _RepairCounter()
            model_session = ModelSession(
                provider=get_ai_provider(),
                prompt_engine=get_prompt_engine(PROMPTS_DIR),
                events=EventBus(),
                model_router=ModelRouter(policy.model_overrides),
                execution_id=f"eval-{case.name}",
            )
            pipeline = EmailCampaignPipeline(
                session=model_session,
                knowledge=_DbKnowledgeGateway(session, campaign),
                policy=policy,
                observer=observer,
            )
            started = time.perf_counter()
            result = await pipeline.run(
                CampaignRequest(
                    name=campaign.name,
                    request=case.request,
                    product_description=case.product_description,
                    target_market=case.target_market,
                    goals=case.goals,
                )
            )
            elapsed = time.perf_counter() - started

    return record_from(case.name, preset, result, elapsed, repairs=observer.repairs)


async def run_all(cases: tuple[GoldenCase, ...], preset: PolicyPreset, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for case in cases:
        print(f"\n=== {case.name} [{preset}] ===", flush=True)
        try:
            record = await run_case(case, preset)
        # One bad case must not end the round: the other cases are the point,
        # and a benchmark that aborts halfway is a benchmark nobody runs.
        except Exception as exc:
            logger.exception("case %s failed", case.name)
            print(f"  !! {case.name} failed: {exc}", flush=True)
            continue
        (out / f"{case.name}.json").write_text(
            record.model_dump_json(indent=2), encoding="utf-8"
        )
        print(f"  {record.summary()}", flush=True)


# ------------------------------------------------------------------- compare


def _load(directory: Path) -> dict[str, RunRecord]:
    return {
        path.stem: RunRecord.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.json"))
    }


def _delta(before: float, after: float, higher_is_better: bool) -> str:
    if before == after:
        return "="
    better = (after > before) if higher_is_better else (after < before)
    return f"{'better' if better else 'WORSE'} ({before:.2f} → {after:.2f})"


def compare(before_dir: Path, after_dir: Path) -> None:
    """Two rounds, side by side.

    Deliberately not a pass/fail: a change that raises pull and cost at the
    same time is a real trade the person making it has to look at, and a
    threshold here would only teach everyone to move the threshold.
    """
    before, after = _load(before_dir), _load(after_dir)
    shared = sorted(set(before) & set(after))
    if not shared:
        print("No cases in common between those two rounds.")
        return

    for name in shared:
        old, new = before[name], after[name]
        print(f"\n{name}")
        print(f"  avg pull            {_delta(old.average_pull, new.average_pull, True)}")
        print(f"  landed rate         {_delta(old.landed_rate, new.landed_rate, True)}")
        print(
            "  first-draft ships   "
            f"{_delta(old.first_draft_ship_rate, new.first_draft_ship_rate, True)}"
        )
        print(f"  model calls         {_delta(old.model_calls, new.model_calls, False)}")
        print(f"  repairs             {_delta(old.repairs, new.repairs, False)}")
        print(f"  cost                {_delta(old.cost_usd, new.cost_usd, False)}")
        print(
            "  cost/shipped email  "
            f"{_delta(old.cost_per_shipped_email, new.cost_per_shipped_email, False)}"
        )
        words_before = [email.word_count for email in old.emails]
        words_after = [email.word_count for email in new.emails]
        if words_before and words_after:
            print(
                "  body words          "
                f"{_delta(sum(words_before) / len(words_before), sum(words_after) / len(words_after), False)}"
            )

    print("\nTotals")
    print(
        f"  cost   ${sum(r.cost_usd for r in before.values()):.2f} → "
        f"${sum(r.cost_usd for r in after.values()):.2f}"
    )
    print(
        f"  calls  {sum(r.model_calls for r in before.values())} → "
        f"{sum(r.model_calls for r in after.values())}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", default="balanced", choices=["fast", "balanced", "maximum"])
    parser.add_argument("--case", help="run one golden case by name")
    parser.add_argument("--out", type=Path, help="directory to write records to")
    parser.add_argument(
        "--compare", nargs=2, type=Path, metavar=("BEFORE", "AFTER"),
        help="compare two previous rounds instead of running anything",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)

    if args.compare:
        compare(*args.compare)
        return 0

    if args.out is None:
        parser.error("--out is required when running cases")

    cases: tuple[GoldenCase, ...] = GOLDEN_CASES
    if args.case:
        chosen = case_named(args.case)
        if chosen is None:
            parser.error(
                f"no golden case named {args.case!r} - "
                f"have: {', '.join(item.name for item in GOLDEN_CASES)}"
            )
        cases = (chosen,)

    print(
        f"Running {len(cases)} case(s) on the {args.preset} preset against REAL models.\n"
        "This spends quota.",
        flush=True,
    )
    asyncio.run(run_all(cases, args.preset, args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
