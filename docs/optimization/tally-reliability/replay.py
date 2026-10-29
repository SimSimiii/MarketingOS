"""Replay saved rows in a disposable database; --dry-run never calls a model.

Run from backend/: .venv/Scripts/python.exe ../docs/optimization/tally-reliability/replay.py --dry-run
The fixed provider-attempt cap includes dossier generation and transport retries.
"""
import argparse
import asyncio
import dataclasses
import json
import os
import sys
import tempfile
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
# Set these before any app import: never initialize the operator's database.
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"

from sqlmodel import SQLModel, Session, create_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.ai.factory import get_ai_provider  # noqa: E402
from app.ai.model_router import ModelRouter  # noqa: E402
from app.core.config import PROMPTS_DIR, get_settings  # noqa: E402
from app.knowledge.store import ArtifactScope, ArtifactStore, fingerprint_documents  # noqa: E402
from app.market.relevance import RelevanceAnalyst  # noqa: E402
from app.marketing.email_copy import render_review  # noqa: E402
from app.marketing.contract import parse_contract  # noqa: E402
from app.marketing.forecast import forecast  # noqa: E402
from app.marketing.observer import RunObserver  # noqa: E402
from app.marketing.pipeline import EmailCampaignPipeline  # noqa: E402
from app.marketing.policy import resolve_policy  # noqa: E402
from app.marketing.render_html import BrandStyle, EmailTier, render_html, style_for_action  # noqa: E402
from app.marketing.request import CampaignRequest  # noqa: E402
from app.models.brand import Brand  # noqa: E402
from app.models.campaign import Campaign  # noqa: E402
from app.models.knowledge_artifacts import KnowledgeArtifactSet  # noqa: E402
from app.models.knowledge_document import KnowledgeDocument  # noqa: E402
from app.models.market import (  # noqa: E402
    AudienceMapRow, AudienceResearchRow, MarketScan, RelevanceDossierRow,
)
from app.orchestration.campaign_orchestrator import _DbKnowledgeGateway  # noqa: E402
from app.runtime.events import EventBus  # noqa: E402
from app.runtime.model_session import ModelSession  # noqa: E402
from app.runtime.prompt_engine import get_prompt_engine  # noqa: E402
from app.runtime.work_limits import WorkLimitError, current_work  # noqa: E402
from app.services.market_service import MarketService  # noqa: E402


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


class Budget:
    def __init__(self, config, output):
        self.config, self.output = config, output
        self.calls = self.tokens = 0
        self.started = time.monotonic()

    def attempt(self):
        if (self.calls >= self.config["max_provider_attempts"]
                or self.tokens >= self.config["max_total_tokens"]
                or time.monotonic() - self.started >= self.config["max_duration_seconds"]):
            raise WorkLimitError("Bounded qualitative replay budget reached")
        self.calls += 1
        self.save()

    def record_usage(self, tokens):
        self.tokens += tokens
        self.save()

    def save(self):
        write(self.output / "budget.json", {
            "provider_attempts": self.calls, "reported_tokens": self.tokens,
            "elapsed_seconds": round(time.monotonic() - self.started, 2),
        })


class Capture(RunObserver):
    def __init__(self, output):
        self.output = output

    def on_phase(self, phase, message, data=None):
        print(f"[{phase}] {message}", flush=True)

    def on_brief(self, brief):
        write(self.output / "brief.json", brief.model_dump(mode="json"))

    def on_draft(self, position, attempt, email):
        write(self.output / f"draft-{position}-{attempt}.json", email.model_dump(mode="json"))

    def on_read(self, position, attempt, panel):
        write(self.output / f"reader-{position}-{attempt}.json", panel.model_dump(mode="json"))

    def on_critique(self, position, attempt, critique):
        write(self.output / f"critique-{position}-{attempt}.json", critique.model_dump(mode="json"))


def prepare(db, config):
    source = ROOT / config["source_snapshot"]
    brand_id = UUID(config["brand_id"])
    db.add(Brand(id=brand_id, name=config["name"]))
    db.commit()
    for filename, model in (
        ("knowledgedocument.json", KnowledgeDocument),
        ("knowledgeartifactset.json", KnowledgeArtifactSet),
        ("marketscan.json", MarketScan),
        ("audiencemaprow.json", AudienceMapRow),
        ("audienceresearchrow.json", AudienceResearchRow),
        ("relevancedossierrow.json", RelevanceDossierRow),
        ("campaign.json", Campaign),
    ):
        for raw in read(source / filename):
            row = dict(raw)
            # SQLite JSON exports can contain JSON encoded as text.
            for key in ("payload", "policy", "model_overrides", "document_metadata", "channel"):
                if isinstance(row.get(key), str):
                    row[key] = json.loads(row[key])
            if "owner_id" in row:
                row["owner_id"] = None
            if "source_type" in row:
                row["source_type"] = row["source_type"].lower()
            if "status" in row:
                row["status"] = row["status"].lower()
            db.add(model.model_validate(row))
        db.commit()
    campaign = db.get(Campaign, UUID(config["campaign_id"]))
    if campaign is None:
        raise ValueError("Configured campaign absent from saved snapshot")
    store = ArtifactStore(db)
    scope = ArtifactScope.for_campaign(campaign)
    # Keep the recorded IDs, but ensure the restored corpus is a cache hit.
    from sqlmodel import select
    row = db.exec(select(KnowledgeArtifactSet).where(KnowledgeArtifactSet.brand_id == brand_id)).first()
    row.source_fingerprint = fingerprint_documents(store.source_documents(scope))
    db.add(row)
    db.commit()
    return campaign


async def replay(case, dry_run):
    config = read(case)
    policy = resolve_policy("fast", {
        "critic_enabled": True, "max_revisions": 1,
        "max_duration_seconds": config["max_duration_seconds"],
        "max_total_tokens": config["max_total_tokens"],
    })
    with tempfile.TemporaryDirectory(prefix="marketingos-replay-") as temporary:
        engine = create_engine(f"sqlite:///{Path(temporary) / 'replay.db'}", poolclass=NullPool)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            campaign = prepare(db, config)
            gateway = _DbKnowledgeGateway(db, campaign)
            service = MarketService(db)
            inputs = service._relevance_inputs(campaign.brand_id, campaign.audience_segment)
            summary = {
                "isolated": True, "knowledge_reused": gateway.load().fingerprint == gateway.fingerprint(),
                "evidence_count": len(inputs.artifacts.evidence.entries),
                "audience": campaign.audience_segment,
                "research_warnings": inputs.research.interpretation_warnings,
                "strategy_positioning_chars": len(inputs.snapshot.positioning.render_for_strategy(campaign.audience_segment)),
                "policy": policy.model_dump(mode="json"), "limits": config,
                "comparison": "Qualitative only; limited review policy and current dossier differ from historical run.",
                "pipeline_forecast": dataclasses.asdict(forecast(
                    policy, parse_contract(campaign.request), knowledge_reused=True,
                )),
                "additional_dossier_calls": 1,
            }
            if dry_run:
                print(json.dumps(summary, ensure_ascii=False, indent=2))
                return
            if get_settings().ai_billing != "subscription" or get_settings().credit_billing_enabled:
                raise RuntimeError("This replay only authorizes subscription billing, without prepaid credits")
            output = case.parent / "runs" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            output.mkdir(parents=True, exist_ok=False)
            write(output / "inputs.json", summary)
            write(output / "campaign.json", campaign.model_dump(mode="json"))
            budget = Budget(config, output)
            token = current_work.set(budget)
            calls = []

            def record(call):
                calls.append(dataclasses.asdict(call))
                write(output / "calls.json", calls)
                print(f"[model] {call.role}: {call.model}; {len(calls)} completed, {budget.calls} attempts", flush=True)

            models = ModelSession(get_ai_provider(), get_prompt_engine(PROMPTS_DIR), EventBus(),
                                  ModelRouter(policy.model_overrides), "snapshot-" + output.name, on_call=record)
            print("Saved run: " + str(output), flush=True)
            try:
                async with asyncio.timeout(config["max_duration_seconds"]):
                    dossier = await RelevanceAnalyst(models).analyse(
                        artifacts=inputs.artifacts,
                        knowledge_id=inputs.knowledge_row.id, knowledge_version=inputs.knowledge_row.version,
                        research=inputs.research, research_id=inputs.research_row.id,
                        research_version=inputs.research_row.version,
                        positioning=inputs.snapshot.positioning,
                        market_scan_id=inputs.market_scan_row.id, market_scan_version=inputs.market_scan_row.version,
                        capability_profile=inputs.capability_profile,
                        capability_profile_id=inputs.capability_profile_row.id,
                        capability_profile_version=inputs.capability_profile_row.version,
                        company_qualifications=inputs.company_qualifications,
                        qualification_fingerprint=inputs.qualification_fingerprint,
                    )
                    write(output / "dossier.json", dossier.model_dump(mode="json"))
                    service.store.save_dossier(campaign.brand_id, dossier)
                    request = CampaignRequest(**{
                        key: getattr(campaign, key) or "" for key in
                        ("name", "request", "product_description", "product_url", "target_market",
                         "goals", "sender_name", "sender_role", "cta_url")
                    })
                    result = await EmailCampaignPipeline(session=models, knowledge=gateway, policy=policy,
                                                         observer=Capture(output)).run(request)
                    write(output / "result.json", {
                        "status": result.status, "abort_reason": result.abort_reason,
                        "report": result.report.model_dump(mode="json"),
                        "brief": result.brief.model_dump(mode="json") if result.brief else None,
                        "emails": [email.model_dump(mode="json") for email in result.emails],
                        "intelligence": result.intelligence.model_dump(mode="json") if result.intelligence else None,
                    })
                    for index, outcome in enumerate(result.outcomes, 1):
                        email = outcome.email
                        style = style_for_action(
                            BrandStyle(name=result.artifacts.business.company_name),
                            explicit_url=campaign.cta_url,
                            planned_action=outcome.selected_brief.call_to_action,
                            offer=result.artifacts.offer,
                            licensed_urls=[entry.source for entry in result.artifacts.evidence.entries],
                        )
                        tier = EmailTier((campaign.policy or {}).get("email_tier", "plain"))
                        (output / f"email-{index}.txt").write_text(render_review(email), encoding="utf-8")
                        (output / f"email-{index}.html").write_text(render_html(email, tier, style), encoding="utf-8")
            except Exception as exc:
                write(output / "error.json", {"type": type(exc).__name__, "message": str(exc)})
                (output / "traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
                raise
            finally:
                budget.save()
                write(output / "calls.json", calls)
                current_work.reset(token)
                print("Saved run: " + str(output), flush=True)
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, default=Path(__file__).with_name("case.json"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    case = args.case.resolve()
    if args.summary:
        paths = sorted((case.parent / "runs").glob("*"))
        if not paths:
            print("No runs recorded")
            return
        latest = paths[-1]
        print(json.dumps({"path": str(latest), "files": [p.name for p in latest.iterdir()],
                          "budget": read(latest / "budget.json")}, indent=2))
        return
    asyncio.run(replay(case, args.dry_run))


if __name__ == "__main__":
    main()
