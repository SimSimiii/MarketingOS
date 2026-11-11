"""Run first-campaign preparation from a saved audit in an isolated SQLite copy."""

import argparse
import asyncio
import json
import sqlite3
from contextlib import closing
from dataclasses import asdict
from pathlib import Path
from tempfile import mkdtemp
from uuid import UUID

from sqlmodel import Session, create_engine

from app.ai.factory import get_ai_provider
from app.core.config import get_settings
from app.market.relevance import recommendation_for_request
from app.services.first_campaign import prepare_first_campaign
from app.services.market_service import JobStatus, MarketService


class ReplayStatus(JobStatus):
    def say(self, message: str) -> None:
        super().say(message)
        print(message, flush=True)

    def record(self, call) -> None:
        super().record(call)
        print(self.log[-1], flush=True)


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if get_settings().ai_billing != "subscription":
        parser.error("Replay requires subscription billing")
    case = json.loads(args.case.read_text(encoding="utf-8-sig"))
    source = Path(case["database"]).resolve(strict=True)
    args.out.mkdir(parents=True)
    database = Path(mkdtemp(prefix="marketingos-preparation-replay-")) / "audit.sqlite"
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original, closing(
        sqlite3.connect(database)
    ) as copy:
        original.backup(copy)
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    brand_id = UUID(case["brand_id"])
    status = ReplayStatus(kind="first_campaign", brand_id=brand_id)
    await prepare_first_campaign(brand_id, get_ai_provider(), engine, status, case["objective"])
    request = f"Write exactly one email. {case['objective']}"
    assessments = {}
    with Session(engine) as session:
        market = MarketService(session)
        for name in dict.fromkeys((case.get("audience_segment"), status.audience)):
            if not name:
                continue
            receipt = market.relevance_status(brand_id, name)
            recommendation = recommendation_for_request(receipt.dossier, request) if receipt.dossier else None
            assessments[name] = {
                "dossier": receipt.model_dump(mode="json"),
                "recommendation": recommendation.model_dump(mode="json") if recommendation else None,
            }
    (args.out / "replay.json").write_text(json.dumps(
        {"database": database.as_posix(), "preparation": asdict(status), "assessments": assessments},
        indent=2, ensure_ascii=False, default=str,
    ) + "\n", encoding="utf-8")
    return 0 if status.state == "done" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
