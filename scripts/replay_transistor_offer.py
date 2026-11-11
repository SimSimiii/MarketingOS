"""Replay planning and copy for the archived Transistor audit in a read-only database."""

import argparse
import asyncio
import json
import sqlite3
from dataclasses import replace
from pathlib import Path
from time import monotonic
from uuid import UUID

from sqlmodel import Session, create_engine

from app.ai.factory import get_ai_provider
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR, get_settings
from app.marketing.briefs import EmailBrief
from app.marketing.email_copy import Email
from app.marketing.gates import mechanical_gate
from app.marketing.grounding import ClaimReviewer, offer_source_excerpts
from app.marketing.pipeline import CampaignRunResult, EmailCampaignPipeline
from app.marketing.policy import PRESETS
from app.models.campaign import Campaign
from app.orchestration.campaign_orchestrator import (
    CampaignOrchestrator,
    _DbKnowledgeGateway,
    campaign_tier,
)
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import get_prompt_engine
from app.services.revision_service import _request_for

CASE = Path(__file__).resolve().parents[1] / "docs/optimization/transistor-cold-v34-validation-2026-11-09"
BASELINE = "3fd73d86-9641-4ac2-891f-f764bce5a6f9"
UNSUPPORTED = "During the free trial, you can host multiple client podcasts in the same account."


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


class ArchivedGateway(_DbKnowledgeGateway):
    def prior_learnings(self) -> str:
        # The original first campaign had no prior report.
        return ""

    def save(self, artifacts, fingerprint):
        raise RuntimeError("The archived knowledge must be reused")


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--negative", type=Path, help="Accepted replay receipt")
    args = parser.parse_args()
    if args.out.exists() or get_settings().ai_billing != "subscription":
        parser.error("Use a new output directory and subscription billing")

    case = load(CASE / "case.json")
    baseline = load(CASE / "runs" / BASELINE / "result.json")
    models = {item["agent_id"]: item["model"] for item in baseline["agent_executions"] if item["model"]}
    database = Path(case["database"]).resolve(strict=True)
    engine = create_engine("sqlite://", creator=lambda: sqlite3.connect(database.as_uri() + "?mode=ro", uri=True))
    with Session(engine) as db:
        campaign = db.get(Campaign, UUID(case["campaign_id"]))
        assert campaign is not None
        gateway = ArchivedGateway(db, campaign)
        stored = gateway.load()
        assert stored is not None and stored.fingerprint == gateway.fingerprint()
        bundle = gateway.campaign_intelligence(stored.artifacts)
        assert bundle is not None and bundle.context.first_email_scope_applied
        excerpts = offer_source_excerpts(
            bundle.artifacts, gateway.corpus(), allowed_ids=set(bundle.context.allowed_evidence_ids),
        )
        assert any("**$19**/mo" in excerpt for excerpt in excerpts.values())
        assert any("All prices in USD. Billed monthly." in excerpt for excerpt in excerpts.values())
        print(json.dumps({"models": models, "captured_offer_excerpts": list(excerpts)}), flush=True)
        if args.dry_run:
            return 0

        args.out.mkdir(parents=True)
        receipt = {"baseline": BASELINE, "models": models}
        calls = []
        started = monotonic()

        def record(call):
            calls.append(call)
            print(f"{call.role}: {call.duration_ms / 1000:.1f}s", flush=True)

        try:
            provider = get_ai_provider()
            session = ModelSession(
                provider, get_prompt_engine(PROMPTS_DIR), EventBus(), ModelRouter(models),
                "transistor-offer-replay", on_call=record,
            )
            policy = PRESETS["fast"]
            async with asyncio.timeout(540):
                if args.negative:
                    accepted = load(args.negative)
                    assert accepted["passed"]
                    brief = EmailBrief.model_validate(accepted["selected_brief"])
                    email = Email.model_validate(accepted["email"])
                    candidate = email.model_copy(update={"body": f"{email.body}\n\n{UNSUPPORTED}"})
                    hints = mechanical_gate(candidate, policy.merge_fields)
                    assert hints.passed
                    report = await ClaimReviewer(session).review(
                        email=candidate, brief=brief, artifacts=bundle.artifacts, corpus=gateway.corpus(), hints=hints,
                    )
                    decision = report.semantic_review["decision"]
                    rejected = not report.passed and (
                        any(UNSUPPORTED in claim["text"] and claim["status"] != "supported"
                            for claim in decision["claims"])
                        or any(UNSUPPORTED in finding["text"] and finding["kind"] == "factual"
                               for finding in decision["findings"])
                    )
                    receipt.update(candidate=candidate.model_dump(mode="json"),
                                   gates=report.model_dump(mode="json"), rejected=rejected)
                    return 0 if rejected else 1

                request = replace(_request_for(campaign), email_tier=campaign_tier(campaign))
                pipeline = EmailCampaignPipeline(session=session, knowledge=gateway, policy=policy)
                contract = pipeline.read_contract(request)
                context, plan = await pipeline.plan(request, contract, CampaignRunResult(usage=session.usage))
                receipt["plan"] = plan.model_dump(mode="json")
                brief = plan.emails[0]
                print(json.dumps({"action": brief.call_to_action, "value": brief.next_step_value,
                                  "decision_conditions": brief.value_case.decision_conditions}), flush=True)
                outcome = await pipeline._craft_loop(
                    context.artifacts, context.corpus, plan, context.positioning,
                ).craft(brief=brief, campaign=plan, request=request, previous=[])
                receipt["versions"] = [
                    {"attempt": v.attempt, "email": v.email.model_dump(mode="json"),
                     "gates": v.gates.model_dump(mode="json"), "read": v.read.model_dump(mode="json")}
                    for v in outcome.versions
                ]
                if not outcome.versions:
                    receipt.update(passed=False, interruption=outcome.interruption)
                    return 1
                selected = outcome.best
                receipt.update(passed=selected.gates.passed, selected_attempt=selected.attempt,
                               email=selected.email.model_dump(mode="json"),
                               selected_brief=outcome.brief.model_dump(mode="json"))
                if not selected.gates.passed:
                    return 1
                content, html, _ = CampaignOrchestrator(db, provider).render_email(
                    campaign, selected.email, outcome.brief, context.artifacts,
                )
                (args.out / "email.txt").write_text(content, encoding="utf-8")
                if html:
                    (args.out / "email.html").write_text(html, encoding="utf-8")
                return 0
        except Exception as exc:
            receipt["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            receipt.update(calls=len(calls), elapsed_seconds=round(monotonic() - started, 3),
                           estimated_usd=sum(call.cost_usd for call in calls))
            (args.out / "replay.json").write_text(
                json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
            )
            print(json.dumps({k: receipt[k] for k in ("passed", "rejected", "calls", "elapsed_seconds", "error")
                              if k in receipt}), flush=True)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
