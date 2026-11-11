"""Replay the original Bannerbear and Canny plans from captured inputs."""

import argparse
import asyncio
import json
import sqlite3
from dataclasses import replace
from pathlib import Path
from time import monotonic
from unittest.mock import patch
from uuid import UUID

from sqlmodel import Session, create_engine

from app.ai.factory import get_ai_provider
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR, get_settings
from app.market.relevance import RelevanceStatus
from app.marketing.briefs import CampaignBrief
from app.marketing.email_copy import Email
from app.marketing.grounding import proposition_source_excerpts
from app.marketing.intelligence import (
    CampaignIntelligenceBundle,
    adapt_researched_audience,
    build_campaign_intelligence,
    resolve_audience_research,
)
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

ARCHIVE = Path(__file__).resolve().parents[1] / "docs/optimization/chatgpt-comparison-2026-11-10"


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


class ArchivedGateway(_DbKnowledgeGateway):
    def __init__(self, session, campaign, relevance):
        super().__init__(session, campaign)
        self.relevance = relevance

    def prior_learnings(self):
        return ""

    def save(self, artifacts, fingerprint):
        raise RuntimeError("The archived knowledge must be reused")

    def campaign_intelligence(self, artifacts):
        brand = self._campaign.brand_id
        audience = self._campaign.audience_segment
        match = resolve_audience_research(audience, self._market.latest_researches(brand))
        segment = self._market.segment_named(brand, audience)
        assert match.research is not None and segment is not None
        context = build_campaign_intelligence(
            selected_audience=audience, selected_need=segment.need, match=match,
            dossier_status=self.relevance, ledger=artifacts.evidence,
            campaign_request=self._campaign.request,
        )
        assert context.first_email_scope_applied
        return CampaignIntelligenceBundle(
            artifacts=adapt_researched_audience(artifacts, match.research, context),
            context=context,
        )


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brand", choices=("bannerbear", "canny"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--draft-from", type=Path, help="Recheck a draft from a saved replay")
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    if args.out and (args.out.exists() or get_settings().ai_billing != "subscription"):
        parser.error("Use a new output directory and subscription billing")

    case_dir = ARCHIVE / args.brand
    case = load(case_dir / "case.json")
    baseline_id = load(case_dir / "state.json")["runs"][0]["execution_id"]
    baseline = load(case_dir / "runs" / baseline_id / "result.json")
    capture = load(next((case_dir / "steps").glob("*-capture.json")))
    relevance = RelevanceStatus.model_validate(capture["relevance"])
    models = {entry["agent_id"]: entry["model"] for entry in baseline["agent_executions"] if entry["model"]}
    database = Path(case["database"]).resolve(strict=True)
    engine = create_engine("sqlite://", creator=lambda: sqlite3.connect(database.as_uri() + "?mode=ro", uri=True))
    with Session(engine) as db:
        campaign = db.get(Campaign, UUID(case["campaign_id"]))
        assert campaign is not None
        gateway = ArchivedGateway(db, campaign, relevance)
        stored = gateway.load()
        assert stored is not None and stored.fingerprint == gateway.fingerprint()
        assert stored.artifacts.version == capture["knowledge"]["artifacts"]["version"]
        # The API can list superseded duplicate pages. Match the effective
        # compiled source set against the original artifact's document IDs.
        assert set(stored.artifacts.source_document_ids) == set(capture["knowledge"]["artifacts"]["source_document_ids"])
        assert {document.id for document in gateway.corpus().documents} <= {
            document["id"] for document in capture["documents"]
        }
        original = CampaignBrief.model_validate(baseline["result"]["brief"]).emails[0]
        excerpts = proposition_source_excerpts(original, stored.artifacts, gateway.corpus())
        print(json.dumps({"baseline": baseline_id, "models": models, "excerpt_count": len(excerpts)}), flush=True)
        if not args.out:
            return 0

        args.out.mkdir(parents=True)
        receipt = {"baseline": baseline_id, "models": models}
        calls = []
        started = monotonic()

        def record(call):
            calls.append(call)
            print(f"{call.role}: {call.duration_ms / 1000:.1f}s", flush=True)

        try:
            provider = get_ai_provider()
            session = ModelSession(
                provider, get_prompt_engine(PROMPTS_DIR), EventBus(), ModelRouter(models),
                f"{args.brand}-proposition-replay", on_call=record,
            )
            request = replace(_request_for(campaign), email_tier=campaign_tier(campaign))
            pipeline = EmailCampaignPipeline(session=session, knowledge=gateway, policy=PRESETS["fast"])
            async with asyncio.timeout(600):
                run = CampaignRunResult(usage=session.usage)
                if args.draft_from:
                    archive = load(args.draft_from)
                    assert archive["baseline"] == baseline_id
                    context = await pipeline.rebuild_context(request, run)
                    plan = CampaignBrief.model_validate(archive["plan"])
                    first_email = Email.model_validate(next(
                        version["email"] for version in archive["versions"] if version["attempt"] == args.attempt
                    ))
                    plan.emails[0].user_request = request.request
                    receipt["draft_replayed"] = str(args.draft_from)
                    receipt["archived_attempt"] = args.attempt
                else:
                    context, plan = await pipeline.plan(request, pipeline.read_contract(request), run)
                receipt["plan"] = plan.model_dump(mode="json")
                brief = plan.emails[0]
                print(json.dumps({"idea": brief.single_idea, "cta": brief.next_step_url}, ensure_ascii=True), flush=True)
                loop = pipeline._craft_loop(context.artifacts, context.corpus, plan, context.positioning)
                craft_args = {"brief": brief, "campaign": plan, "request": request, "previous": []}
                if args.draft_from:
                    # Recheck the exact old words, then use normal production
                    # repair and independent review if the draft still fails.
                    with patch.object(loop, "_draft", return_value=first_email):
                        outcome = await loop.craft(**craft_args)
                else:
                    outcome = await loop.craft(**craft_args)
                receipt["versions"] = [
                    {"attempt": version.attempt, "email": version.email.model_dump(mode="json"),
                     "gates": version.gates.model_dump(mode="json"), "read": version.read.model_dump(mode="json")}
                    for version in outcome.versions
                ]
                selected = outcome.best
                receipt.update(
                    passed=selected.gates.passed, selected_attempt=selected.attempt,
                    selected_brief=outcome.brief.model_dump(mode="json"), landed=selected.ships,
                )
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
            receipt.update(calls=len(calls), elapsed_seconds=round(monotonic() - started, 3))
            (args.out / "replay.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                                                 encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
