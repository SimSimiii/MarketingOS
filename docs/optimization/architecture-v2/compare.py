"""Three-arm isolated comparison. Default is free; --run explicitly spends quota.

Run from backend/, one arm per invocation. Each case shares its provider-attempt,
token and elapsed-time ceiling across all arms. No application DB is opened.
"""
import argparse
import asyncio
import dataclasses
import hashlib
import inspect
import json
import os
import sys
import tempfile
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def configure(args, temporary):
    backend = ROOT / "backend"
    if args.arm == "baseline":
        state = read(HERE / "state.json")
        archive = ROOT / state["baseline_archive"]
        if hashlib.sha256(archive.read_bytes()).hexdigest() != state["baseline_sha256"]:
            raise RuntimeError("Baseline source hash mismatch")
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                if not name.startswith(("backend/app/", "backend/prompts/")) or ".." in Path(name).parts:
                    raise RuntimeError("Unexpected archive member")
            bundle.extractall(temporary)
        backend = Path(temporary) / "backend"
    sys.path.insert(0, str(backend))
    os.environ["APP_ENV"] = "test"
    os.environ["DATABASE_URL"] = "sqlite://"


async def evaluate(args):
    from app.ai.factory import get_ai_provider
    from app.ai.model_router import ModelRouter
    from app.core.config import PROMPTS_DIR, get_settings
    from app.knowledge.artifacts import KnowledgeArtifacts
    from app.knowledge.corpus import Document, SourceCorpus
    from app.knowledge.ledger import EvidenceIndex
    from app.knowledge.store import StoredArtifacts
    from app.market.positioning import PositioningMap
    from app.marketing.briefs import CampaignBrief, EmailBrief
    from app.marketing.contract import parse_contract
    from app.marketing.craft import EmailOutcome, EmailVersion
    from app.marketing.email_copy import render_review
    from app.marketing.gates import run_all
    from app.marketing.intelligence import CampaignIntelligence, CampaignIntelligenceBundle
    from app.marketing.observer import RunObserver
    from app.marketing.pipeline import CampaignRunResult, EmailCampaignPipeline, KnowledgeGateway
    from app.marketing.policy import resolve_policy
    from app.marketing.reader import BlindReader, personas_for
    from app.marketing.render_html import BrandStyle, EmailTier, render_html, style_for_action
    from app.marketing.request import CampaignRequest
    from app.marketing.writer import EmailWriter
    from app.runtime.events import EventBus
    from app.runtime.model_session import ModelSession
    from app.runtime.prompt_engine import get_prompt_engine
    from app.runtime.work_limits import WorkLimitError, current_work

    frozen_path = HERE / "inputs" / f"{args.case}.json"
    frozen = read(frozen_path)
    artifacts = KnowledgeArtifacts.model_validate(frozen["artifacts"])
    doc_fields = {field.name for field in dataclasses.fields(Document)}
    corpus = SourceCorpus.from_documents([Document(**{key: value for key, value in doc.items() if key in doc_fields}) for doc in frozen["documents"]])
    fingerprint = hashlib.sha256(corpus.text.encode()).hexdigest()
    intent = frozen["request"].get("intent")
    raw_request = dict(frozen["request"])
    if intent:
        # Same stated information for all arms, including the older request
        # type that cannot accept the structured intent field.
        raw_request["request"] += "\nUser-supplied campaign context: " + json.dumps(intent, ensure_ascii=False)
        if "intent" in inspect.signature(CampaignRequest).parameters:
            from app.marketing.intent import CampaignIntent
            raw_request["intent"] = CampaignIntent.model_validate(intent)
    request = CampaignRequest(**{key: value for key, value in raw_request.items() if key in inspect.signature(CampaignRequest).parameters})
    policy = resolve_policy("fast", {"critic_enabled": args.arm != "simple", "max_revisions": 0 if args.arm == "simple" else 1,
        "max_duration_seconds": 1200, "max_total_tokens": 750000,
        "strategy_mode": "direct" if args.arm == "direct" else "planned"})
    limits = {"attempts": 4, "tokens": 150000, "seconds": 300} if args.arm == "direct" else {"attempts": 24, "tokens": 750000, "seconds": 1800}
    manifest = {"arm": args.arm, "case": args.case, "input_sha256": hashlib.sha256(frozen_path.read_bytes()).hexdigest(),
                "policy": policy.model_dump(mode="json"), "source": frozen["source"], "split": frozen["split"],
                "group_limits": limits, "compiled_knowledge_reused": True,
                "limitation": "One stochastic output per arm is a qualitative comparison, not a statistical conversion experiment."}
    if not args.run:
        print(json.dumps(manifest, indent=2))
        return
    if get_settings().ai_billing != "subscription" or get_settings().credit_billing_enabled:
        raise RuntimeError("Only subscription quota is authorized")
    group = HERE / "comparisons" / args.group / args.case
    output = group / args.arm
    output.mkdir(parents=True, exist_ok=False)
    write(output / "manifest.json", manifest)
    write(output / "input.json", frozen)
    calls = []
    started = time.monotonic()

    class Budget:
        def __init__(self):
            path = group / "budget.json"
            self.value = read(path) if path.exists() else {"attempts": 0, "tokens": 0, "seconds": 0}
            self.previous_seconds = self.value["seconds"]
        def save(self):
            self.value["seconds"] = round(self.previous_seconds + time.monotonic() - started, 2)
            write(group / "budget.json", self.value)
        def attempt(self):
            self.save()
            if self.value["attempts"] >= limits["attempts"] or self.value["tokens"] >= limits["tokens"] or self.value["seconds"] >= limits["seconds"]:
                raise WorkLimitError("Shared comparison budget reached")
            self.value["attempts"] += 1
            self.save()
        def record_usage(self, tokens):
            self.value["tokens"] += tokens
            self.save()

    class Gateway(KnowledgeGateway):
        def corpus(self): return corpus
        def fingerprint(self): return fingerprint
        def load(self): return StoredArtifacts(artifacts=artifacts, version=1, fingerprint=fingerprint)
        def save(self, compiled, fp): raise RuntimeError("Frozen evidence must not be recompiled")
        def audience_choice(self): return frozen.get("selected_audience", "")
        def positioning(self):
            return PositioningMap.model_validate(frozen["positioning"]) if frozen.get("positioning") else None
        def campaign_intelligence(self, found):
            if frozen.get("intelligence"):
                return CampaignIntelligenceBundle(artifacts=found, context=CampaignIntelligence.model_validate(frozen["intelligence"]))
            return None

    class Capture(RunObserver):
        def on_phase(self, phase, message, data=None):
            print(f"[{args.case}/{args.arm}/{phase}] {message}", flush=True)
            with (output / "phases.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"phase": phase, "message": message, "data": data}, ensure_ascii=False, default=str) + "\n")
        def on_brief(self, brief): write(output / "brief.json", brief.model_dump(mode="json"))
        def on_draft(self, position, attempt, email): write(output / f"draft-{position}-{attempt}.json", email.model_dump(mode="json"))
        def on_read(self, position, attempt, panel): write(output / f"reader-{position}-{attempt}.json", panel.model_dump(mode="json"))
        def on_critique(self, position, attempt, critique): write(output / f"critique-{position}-{attempt}.json", critique.model_dump(mode="json"))

    def record(call):
        calls.append(dataclasses.asdict(call))
        write(output / "calls.json", calls)
        print(f"[{args.case}/{args.arm}] {call.role}: {len(calls)} completed", flush=True)

    budget = Budget()
    token = current_work.set(budget)
    models = ModelSession(get_ai_provider(), get_prompt_engine(PROMPTS_DIR), EventBus(), ModelRouter(policy.model_overrides),
                          "architecture-" + args.group + "-" + args.case + "-" + args.arm, on_call=record)
    observer = Capture()
    pipeline = EmailCampaignPipeline(session=models, knowledge=Gateway(), policy=policy, observer=observer)
    try:
        async with asyncio.timeout(min(1200, limits["seconds"])):
            if args.arm == "simple":
                # One direct draft and one independent read, no strategic or
                # critic call. Factual checks still apply against the same data.
                brief = EmailBrief(job=request.request, evidence_ids=[])
                campaign = CampaignBrief(reader=request.target_market or frozen.get("selected_audience", ""),
                                         reader_profile_override=request.target_market or frozen.get("selected_audience", ""),
                                         orientation=artifacts.business.what_it_does, emails=[brief])
                email = await EmailWriter(models, observer).draft(brief=brief, campaign=campaign, request=request, artifacts=artifacts, previous=[])
                panel = await BlindReader(models).read(email, personas_for(artifacts.audience, None, False,
                    explicit_audience=campaign.reader_profile_override))
                gates, support = run_all(email, evidence=EvidenceIndex(artifacts.evidence, corpus.text),
                    offer=artifacts.offer, business=artifacts.business, previous=[], merge_fields=policy.merge_fields, assigned=[])
                version = EmailVersion(attempt=1, email=email, gates=gates, read=panel, substantiation=support)
                outcome = EmailOutcome(brief=brief, versions=[version])
                result = CampaignRunResult(artifacts=artifacts, brief=campaign, outcomes=[outcome])
                result.report = pipeline._build_report(request, parse_contract(request.request), result)
                result.status = "completed" if result.report.healthy else "degraded"
                observer.on_draft(1, 1, email)
                observer.on_read(1, 1, panel)
            else:
                result = await pipeline.run(request)
            write(output / "result.json", {"status": result.status, "abort_reason": result.abort_reason,
                "report": result.report.model_dump(mode="json"), "brief": result.brief.model_dump(mode="json") if result.brief else None,
                "emails": [email.model_dump(mode="json") for email in result.emails]})
            for index, outcome in enumerate(result.outcomes, 1):
                brief = outcome.selected_brief
                style = style_for_action(BrandStyle(name=artifacts.business.company_name), explicit_url=request.cta_url,
                    planned_action=getattr(brief, "next_step_url", "") or brief.call_to_action, offer=artifacts.offer,
                    licensed_urls=[entry.source for entry in artifacts.evidence.entries])
                (output / f"email-{index}.txt").write_text(render_review(outcome.email), encoding="utf-8")
                (output / f"email-{index}.html").write_text(render_html(outcome.email, EmailTier.BRANDED, style), encoding="utf-8")
    except BaseException as exc:
        write(output / "error.json", {"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        budget.save()
        current_work.reset(token)
        write(output / "usage.json", {"calls": len(calls), "reported_tokens": sum(call["input_tokens"] + call["output_tokens"] + call.get("cache_read_input_tokens", 0) + call.get("cache_creation_input_tokens", 0) for call in calls),
            "seconds": round(time.monotonic() - started, 2), "catalogue_equivalent_usd": sum(call.get("cost_usd", 0) for call in calls)})
    print("Saved: " + str(output), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--arm", choices=("baseline", "proposed", "simple", "direct"), required=True)
    parser.add_argument("--group", default=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="marketingos-baseline-") as temporary:
        configure(args, temporary)
        asyncio.run(evaluate(args))
