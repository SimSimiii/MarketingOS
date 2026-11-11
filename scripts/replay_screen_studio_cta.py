"""Replay Screen Studio's rejected draft or check its accepted export with a false claim."""

import argparse
import asyncio
import json
from pathlib import Path
from time import monotonic

from replay_scribe_factual_repair import ArchivedFirstDraft, load

from app.ai.factory import get_ai_provider
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR, get_settings
from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.corpus import Document, SourceCorpus
from app.knowledge.ledger import EvidenceIndex
from app.marketing.briefs import CampaignBrief
from app.marketing.craft import EmailVersion
from app.marketing.email_copy import Email, render_email, render_review
from app.marketing.gates import GateReport
from app.marketing.policy import PRESETS
from app.marketing.reader import BlindRead, BlindReader, PanelRead
from app.marketing.render_html import BrandStyle, EmailTier, render_html, style_for_action
from app.marketing.request import CampaignRequest
from app.marketing.writer import EmailWriter
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import get_prompt_engine

CASE = Path(__file__).resolve().parents[1] / "docs/optimization/screen-studio-cold-v33-validation-2026-11-09"
RUN = CASE / "runs/5ce928b9-c140-4fcf-973e-38362c2532b7"
BRAND_SNAPSHOT = CASE / "steps/20261109T103336020378Z-capture.json"
FALSE_PROMISE = "Download and export your first video for free."


def saved_brand_style() -> BrandStyle:
    brand = load(BRAND_SNAPSHOT)["brand"]
    return BrandStyle(
        name=brand["name"], logo_url=brand["logo_url"], website_url=brand["website_url"],
        primary_color=brand["primary_color"], footer_lines=tuple(brand["footer_lines"] or ()),
        cta_url=brand["website_url"], unsubscribe_url=brand["unsubscribe_url"] or "",
    )


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--negative", type=Path, help="Replay receipt for the accepted email")
    args = parser.parse_args()
    if args.out.exists() or get_settings().ai_billing != "subscription":
        parser.error("Use a new output directory and subscription billing")

    result = load(RUN / "result.json")
    campaign = CampaignBrief.model_validate(result["result"]["brief"])
    brief = campaign.emails[0]
    first = {event["type"]: event for event in load(RUN / "timeline.json")["events"]
             if event.get("attempt") == 1 and event["type"] in {"draft", "gates", "review"}}
    gates = GateReport.model_validate(first["gates"])
    claims = gates.semantic_review["decision"]["claims"]
    # The timeline stores the body and delivery fields. Recover the display
    # headline from the exact text cited in the first draft's receipt.
    email = Email.model_validate({**first["draft"], "headline": claims[2]["text"]})
    assert all(claim["text"] in render_review(email) for claim in claims)
    read = PanelRead(reads=[BlindRead.model_validate(item) for item in first["review"]["readers"]])
    archived = EmailVersion(attempt=1, email=email, gates=gates, read=read, idea=brief.single_idea)
    artifacts = KnowledgeArtifacts.model_validate(load(CASE / "knowledge-initial.json")["artifacts"])
    corpus = SourceCorpus.from_documents([
        Document(id=d["id"], title=d["title"], content=d["content"], source=d["source_url"],
                 source_type=d["source_type"])
        for d in load(CASE / "documents-full.json")
    ])
    saved_request = load(RUN / "campaign.json")
    request = CampaignRequest(
        name=saved_request["name"], request=saved_request["request"],
        email_tier=EmailTier(saved_request["email_tier"]), cta_url=saved_request["cta_url"],
    )
    style = style_for_action(
        saved_brand_style(), explicit_url=request.cta_url, planned_action=brief.next_step_url,
        offer=artifacts.offer, require_planned_destination=True,
    )
    assert style.cta_url == "https://screen.studio/download"
    models = {item["agent_id"]: item["model"] for item in result["agent_executions"] if item["model"]}
    calls = []
    session = ModelSession(
        get_ai_provider(), get_prompt_engine(PROMPTS_DIR), EventBus(), ModelRouter(models),
        "screen-studio-cta-replay", on_call=calls.append,
    )
    policy = PRESETS["fast"]
    loop = ArchivedFirstDraft(
        archived, writer=EmailWriter(session), reader=BlindReader(session), critic=None,
        artifacts=artifacts, evidence=EvidenceIndex(artifacts.evidence, corpus.text),
        corpus=corpus, personas=[item.persona for item in read.reads], merge_fields=policy.merge_fields,
        max_revisions=policy.max_revisions, candidates=policy.draft_candidates,
    )
    repair = loop._repair_for(archived, brief)
    assert repair is not None
    print(json.dumps({"models": models, "destination": style.cta_url,
                      "supported_passages": len(repair.supported_passages)}), flush=True)
    if args.dry_run:
        return

    args.out.mkdir(parents=True)
    started = monotonic()
    receipt = {"archived_run": result["id"], "models": models, "destination": style.cta_url}
    try:
        if args.negative:
            replay = load(args.negative)
            assert replay["passed"]
            accepted = Email.model_validate(replay["email"])
            candidate = accepted.model_copy(update={"body": f"{accepted.body}\n\n{FALSE_PROMISE}"})
            checked, _ = loop._check(candidate, brief, [])
            assert checked.passed, "The negative control must reach the AI source review"
            report = await loop._review_claims(candidate, brief, checked)
            decision = report.semantic_review["decision"]
            rejected = (
                not report.passed
                and all(issue.gate != "review-reference" for issue in report.blocking)
                and (
                    any(claim["status"] != "supported" and "export" in claim["text"].lower()
                        and "free" in claim["text"].lower() for claim in decision["claims"])
                    or any(finding["kind"] == "factual" and "export" in finding["text"].lower()
                           and "free" in finding["text"].lower() for finding in decision["findings"])
                )
            )
            receipt.update(candidate=candidate.model_dump(mode="json"),
                           gates=report.model_dump(mode="json"), rejected=rejected)
            return 0 if rejected else 1

        outcome = await loop.craft(brief=brief, campaign=campaign, request=request, previous=[])
        latest = outcome.versions[-1]
        decision = (latest.gates.semantic_review or {}).get("decision") or {}
        retention = decision.get("benefit_retention") or {}
        passed = latest.gates.passed and retention.get("status") == "preserved" and outcome.best.attempt != 1
        receipt.update(
            passed=passed, selected_attempt=outcome.best.attempt, retention=retention,
            email=outcome.email.model_dump(mode="json"),
            versions=[{"attempt": version.attempt, "email": version.email.model_dump(mode="json"),
                       "gates": version.gates.model_dump(mode="json"), "read": version.read.model_dump(mode="json")}
                      for version in outcome.versions],
        )
        if passed:
            (args.out / "email.txt").write_text(render_email(outcome.email, cta_url=style.cta_url), encoding="utf-8")
            (args.out / "email.html").write_text(
                render_html(outcome.email, tier=request.email_tier, brand=style), encoding="utf-8",
            )
        return 0 if passed else 1
    except Exception as exc:
        receipt["error"] = str(exc)
        raise
    finally:
        receipt.update(calls=len(calls), elapsed_seconds=round(monotonic() - started, 3),
                       estimated_usd=sum(call.cost_usd for call in calls))
        (args.out / "replay.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        print(json.dumps({key: receipt[key] for key in
                          ("passed", "rejected", "selected_attempt", "calls", "elapsed_seconds") if key in receipt}),
              flush=True)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
