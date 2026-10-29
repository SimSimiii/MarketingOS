"""Freeze six inputs; optional single bounded dossier call, never the product DB."""
import argparse
import asyncio
import dataclasses
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"

from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import NullPool
from app.knowledge.artifacts import KnowledgeArtifacts
from app.marketing.request import CampaignRequest
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import get_prompt_engine
from app.runtime.work_limits import current_work
from app.ai.factory import get_ai_provider
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR, get_settings
from app.market.relevance import RelevanceAnalyst, RelevanceDossier
from app.orchestration.campaign_orchestrator import _DbKnowledgeGateway
from app.services.market_service import MarketService

spec = importlib.util.spec_from_file_location("saved_replay", ROOT / "docs/optimization/tally-reliability/replay.py")
saved = importlib.util.module_from_spec(spec)
spec.loader.exec_module(saved)
HERE = Path(__file__).resolve().parent


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def synthetic_cases():
    # Explicit synthetic fixtures, not claims about real businesses.
    rows = [
        ("b2b-acquisition", "Repairboard", "a shared repair-status board", "acquisition", "cold",
         "Write exactly one email introducing the repair-status board to independent repair shop owners. Invite a relevant first evaluation, without assuming they already have a software project.",
         "Independent repair shop owners considering how customers can inspect repair stages.",
         ["Repairboard displays each repair's current stage on a shared board.", "A shop can share a read-only status link with its customer."], "View a sample repair board", "https://repairboard.example/sample"),
        ("activation", "Portway", "a searchable workspace for shared-drive files", "activation", "customer",
         "Write exactly one onboarding email helping a new account connect its first drive and understand when search becomes available.",
         "A new account administrator who has signed up but has not connected a drive.",
         ["Connect a drive and Portway indexes it in the background.", "Search works as soon as the first folder finishes indexing."], "Connect a drive", "https://portway.example/connect"),
        ("cart-recovery", "CanvasTrail", "a canvas weekend bag", "recovery", "prospect",
         "Write exactly one friendly abandoned-cart reminder for the weekend bag. Invite the reader to return to their basket, without inventing urgency, discounts or why they stopped.",
         "People who left the weekend bag in their basket without completing checkout.",
         ["The CanvasTrail weekend bag has a removable shoulder strap and an internal zipped pocket.", "The weekend bag costs EUR 80. Shipping charges are shown at checkout."], "Return to your basket", "https://canvastrail.example/basket"),
        ("consumer-offer", "ClayRoom", "a pottery workshop for beginners", "announcement", "subscriber",
         "Write exactly one email presenting the beginner pottery workshop to local newsletter subscribers. Explain what they can try and invite them to inspect the programme.",
         "Local adults interested in trying a creative weekend activity; no employer or business buying process is established.",
         ["ClayRoom's beginner workshop includes clay, tools and an instructor-led introduction to hand building.", "Finished pieces are collected after firing; the workshop does not include a pottery wheel session."], "View the workshop programme", "https://clayroom.example/programme"),
        ("thin-service", "Ledgerloop", "a bookkeeping support service", "custom", "unknown",
         "Write exactly one short email introducing our bookkeeping support service to small business owners and inviting a reply about their bookkeeping question. We have no documented customer outcomes or service package details. Keep the scope honest.",
         "Small business owners considering bookkeeping support.",
         ["Ledgerloop offers bookkeeping support for small businesses."], "Reply with your bookkeeping question", None),
    ]
    for case_id, name, offering, objective, relationship, request, audience, facts, label, url in rows:
        source = f"https://{name.lower()}.example/offer"
        entries = [{"id": f"E{i}", "kind": "price" if "EUR 80" in fact else "feature",
                    "claim": fact, "verbatim": fact, "source": source, "document_id": "synthetic-source",
                    "context": {"subject": name, "source_kind": "official_documentation", "claim_scope": "documented_capability", "verification": "fixture_exact_quote"}}
                   for i, fact in enumerate(facts, 1)]
        artifacts = KnowledgeArtifacts.model_validate({"business": {"company_name": name, "what_it_does": offering},
            "offer": {"calls_to_action": [{"label": label, "url": url, "intent": label}]},
            "evidence": {"entries": entries}, "audience": {"segments": [{"name": audience}]}})
        yield case_id, {"id": case_id, "source": "labelled synthetic fixture", "split": "holdout" if case_id in {"cart-recovery", "consumer-offer", "thin-service"} else "development",
            "request": {"name": name, "request": request, "target_market": audience,
                        "intent": {"objective": objective, "reader_relationship": relationship}},
            "artifacts": artifacts.model_dump(mode="json"), "documents": [{"id": "synthetic-source", "title": "Synthetic offer", "source": source,
                "content": "\n\n".join(facts) + f"\n\n{label}: {url or 'reply to this email'}"}], "selected_audience": ""}


async def main(refresh, rebind=False):
    inputs_dir = HERE / "inputs"
    for case_id, value in synthetic_cases():
        
        if not (inputs_dir / f"{case_id}.json").exists():
            write(inputs_dir / f"{case_id}.json", value)
    target = inputs_dir / ("tally-announcement-v2.json" if rebind else "tally-announcement.json")
    if target.exists():
        print("Six frozen inputs already available; Tally input preserved.")
        return
    config = saved.read(ROOT / "docs/optimization/tally-reliability/case.json")
    with tempfile.TemporaryDirectory(prefix="marketingos-architecture-inputs-") as folder:
        engine = create_engine(f"sqlite:///{Path(folder).as_posix()}/case.db", poolclass=NullPool)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            campaign = saved.prepare(db, config)
            gateway = _DbKnowledgeGateway(db, campaign)
            service = MarketService(db)
            inputs = service._relevance_inputs(campaign.brand_id, campaign.audience_segment)
            if not refresh and not rebind:
                print("Five synthetic inputs prepared. Tally requires --refresh-dossier after scripted validation; maximum4 attempts,200000 tokens,600 seconds.")
                return
            if rebind:
                from app.knowledge.ledger import context_of
                original = saved.read(HERE / "common-dossier/dossier.json")
                dossier = RelevanceDossier.model_validate(original)
                for ref in dossier.evidence:
                    entry = inputs.artifacts.evidence.get(ref.id)
                    if entry is None or entry.verbatim != ref.verbatim or entry.source != ref.source or context_of(entry) != ref.context:
                        raise RuntimeError("Common dossier source/scope changed; cannot reuse its semantic decisions")
                dossier = dossier.model_copy(update={"capability_profile_id": inputs.capability_profile_row.id,
                    "capability_profile_version": inputs.capability_profile_row.version,
                    "qualification_fingerprint": inputs.qualification_fingerprint})
                service.store.save_dossier(campaign.brand_id, dossier)
                status = service.relevance_status(campaign.brand_id, campaign.audience_segment)
                if str(status.status) != "current":
                    raise RuntimeError("Rebound current dossier is unexpectedly stale: " + str(status.stale_reasons))
                write(HERE / "common-dossier/rebind.json", {"reason": "Read adapter now uses the same refreshed source context as profile creation; no source or semantic decision changed", "original_profile_id": original["capability_profile_id"], "new_profile_id": str(dossier.capability_profile_id), "status": str(status.status)})
            else:
                if get_settings().ai_billing != "subscription" or get_settings().credit_billing_enabled:
                    raise RuntimeError("Subscription-only evaluation")
                output = HERE / "common-dossier"
                output.mkdir(exist_ok=False)
                budget = saved.Budget({"max_provider_attempts": 4, "max_total_tokens": 200000, "max_duration_seconds": 600}, output)
                calls = []
                def record(call):
                    calls.append(dataclasses.asdict(call))
                    write(output / "calls.json", calls)
                model = ModelSession(get_ai_provider(), get_prompt_engine(PROMPTS_DIR), EventBus(), ModelRouter({"*": "gpt-5.6-sol"}), "architecture-common-dossier", on_call=record)
                token = current_work.set(budget)
                try:
                    async with asyncio.timeout(600):
                        dossier = await RelevanceAnalyst(model).analyse(
                            artifacts=inputs.artifacts, knowledge_id=inputs.knowledge_row.id, knowledge_version=inputs.knowledge_row.version,
                            research=inputs.research, research_id=inputs.research_row.id, research_version=inputs.research_row.version,
                            positioning=inputs.snapshot.positioning, market_scan_id=inputs.market_scan_row.id, market_scan_version=inputs.market_scan_row.version,
                            capability_profile=inputs.capability_profile, capability_profile_id=inputs.capability_profile_row.id,
                            capability_profile_version=inputs.capability_profile_row.version, company_qualifications=inputs.company_qualifications,
                            qualification_fingerprint=inputs.qualification_fingerprint)
                    service.store.save_dossier(campaign.brand_id, dossier)
                    write(output / "dossier.json", dossier.model_dump(mode="json"))
                finally:
                    budget.save()
                    current_work.reset(token)
            bundle = gateway.campaign_intelligence(inputs.artifacts)
            request = CampaignRequest(**{key: getattr(campaign, key) or "" for key in
                ("name", "request", "product_description", "product_url", "target_market", "goals", "sender_name", "sender_role", "cta_url")})
            write(target, {"id": "tally-announcement", "source": "recorded Tally corpus and original request; one common current dossier for every arm", "split": "development",
                "request": dataclasses.asdict(request), "selected_audience": campaign.audience_segment,
                "artifacts": bundle.artifacts.model_dump(mode="json"), "intelligence": bundle.context.model_dump(mode="json"),
                "positioning": inputs.snapshot.positioning.model_dump(mode="json"),
                "documents": [dataclasses.asdict(doc) for doc in gateway.corpus().documents]})
        engine.dispose()
    print("Six frozen inputs prepared; one common Tally dossier.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-dossier", action="store_true")
    parser.add_argument("--rebind-common", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.refresh_dossier, args.rebind_common))
