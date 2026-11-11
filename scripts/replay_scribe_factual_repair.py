"""Replay the saved Scribe draft through the production repair loop, without a campaign."""

import argparse
import asyncio
import json
from pathlib import Path
from time import monotonic

from app.ai.factory import get_ai_provider
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR, get_settings
from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.corpus import Document, SourceCorpus
from app.knowledge.ledger import EvidenceIndex
from app.marketing.briefs import CampaignBrief, EmailBrief
from app.marketing.craft import CraftLoop, EmailVersion
from app.marketing.email_copy import Email, render_email, render_review
from app.marketing.gates import GateReport
from app.marketing.policy import PRESETS
from app.marketing.reader import BlindRead, BlindReader, PanelRead
from app.marketing.request import CampaignRequest
from app.marketing.writer import EmailWriter
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import get_prompt_engine

CASE = Path(__file__).resolve().parents[1] / "docs/optimization/scribe-cold-v32-validation-2026-11-09"
RUN = CASE / "runs/1cfaae71-2f1d-4184-acc7-aee851c84aa3"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class ArchivedFirstDraft(CraftLoop):
    def __init__(self, archive: EmailVersion, **kwargs):
        super().__init__(**kwargs)
        self.archive = archive

    async def _first_draft(self, brief, campaign, request, previous):
        prior = self.archive
        return prior.email, (prior.gates, prior.substantiation, prior.read), [], brief.single_idea


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    review = parser.add_mutually_exclusive_group()
    review.add_argument("--review-old-rewrite", action="store_true",
                        help="Check the saved rewrite that lost the benefit")
    review.add_argument("--review-repaired", type=Path,
                        help="Recheck the selected email from an earlier repair replay")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out already exists; preserve the previous attempt")
    if get_settings().ai_billing != "subscription":
        parser.error("This replay requires subscription billing")

    events = load(RUN / "timeline.json")["events"]
    first = {event["type"]: event for event in events if event.get("attempt") == 1
             and event["type"] in {"draft", "gates", "review"}}
    result = load(RUN / "result.json")
    brief = EmailBrief.model_validate(result["assets"][0]["asset_metadata"]["selected_brief"])
    campaign = CampaignBrief.model_validate(result["result"]["brief"])
    gates = GateReport.model_validate(first["gates"])
    claims = gates.semantic_review["decision"]["claims"]
    # The draft event stores the body and delivery fields. The next two
    # passages after subject and preview in the receipt are the display headings.
    # Non-visible role and language labels were not archived for rejected drafts.
    email = Email.model_validate({
        **first["draft"], "eyebrow": claims[2]["text"], "headline": claims[3]["text"],
    })
    assert all(claim["text"] in render_review(email) for claim in claims)
    read = PanelRead(reads=[BlindRead.model_validate(r) for r in first["review"]["readers"]])
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
        email_tier=saved_request["email_tier"], cta_url=saved_request["cta_url"],
    )
    models = {item["agent_id"]: item["model"] for item in result["agent_executions"] if item["model"]}
    calls = []
    session = ModelSession(
        get_ai_provider(), get_prompt_engine(PROMPTS_DIR), EventBus(), ModelRouter(models),
        "scribe-factual-repair-replay", on_call=calls.append,
    )
    policy = PRESETS["fast"]
    loop = ArchivedFirstDraft(
        archived, writer=EmailWriter(session), reader=BlindReader(session), critic=None,
        artifacts=artifacts, evidence=EvidenceIndex(artifacts.evidence, corpus.text),
        corpus=corpus, personas=[r.persona for r in read.reads], merge_fields=policy.merge_fields,
        max_revisions=policy.max_revisions, candidates=policy.draft_candidates,
    )
    repair = loop._repair_for(archived, brief)
    assert repair is not None, "No original supported claim could be resolved against the archived sources"
    print(json.dumps({"models": models, "supported_passages": len(repair.supported_passages),
                      "rejected_passages": len(gates.blocking)}, ensure_ascii=False), flush=True)
    if args.dry_run:
        return

    args.out.mkdir(parents=True)
    started = monotonic()
    receipt = {"archived_run": result["id"], "original": email.model_dump(mode="json"),
               "original_gates": gates.model_dump(mode="json"), "models": models}
    try:
        if args.review_old_rewrite or args.review_repaired:
            if args.review_old_rewrite:
                candidate = Email.model_validate(result["assets"][0]["asset_metadata"])
                expected = "lost"
            else:
                replay = load(args.review_repaired)
                candidate = Email.model_validate(next(
                    v["email"] for v in replay["versions"] if v["attempt"] == replay["selected_attempt"]
                ))
                expected = "preserved"
            checked, _ = loop._check(candidate, brief, [])
            reviewed = await loop._review_claims(candidate, brief, checked, repair)
            receipt["candidate"] = candidate.model_dump(mode="json")
            receipt["fresh_review"] = reviewed.model_dump(mode="json")
            retention = (reviewed.semantic_review or {}).get("decision", {}).get("benefit_retention") or {}
            print(json.dumps({"passed": reviewed.passed, "retention": retention, "calls": len(calls)},
                             ensure_ascii=False), flush=True)
            if (not reviewed.passed or retention.get("status") != expected
                    or bool(reviewed.advisory) != (expected == "lost")):
                raise SystemExit(1)
            return
        outcome = await loop.craft(brief=brief, campaign=campaign, request=request, previous=[])
        receipt["versions"] = [
            {"attempt": v.attempt, "email": v.email.model_dump(mode="json"),
             "gates": v.gates.model_dump(mode="json"), "read": v.read.model_dump(mode="json")}
            for v in outcome.versions
        ]
        receipt["selected_attempt"] = outcome.best.attempt
        if outcome.best.gates.passed and outcome.best.attempt != 1:
            content = render_email(outcome.email, cta_url=brief.next_step_url)
            (args.out / "email.txt").write_text(content, encoding="utf-8")
    except Exception as exc:
        receipt["error"] = str(exc)
        raise
    finally:
        receipt.update(calls=len(calls), elapsed_seconds=round(monotonic() - started, 3),
                       estimated_usd=sum(call.cost_usd for call in calls))
        (args.out / "replay.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
    latest = outcome.versions[-1]
    final_review = latest.gates.semantic_review or {}
    retention = (final_review.get("decision") or {}).get("benefit_retention") or {}
    print(json.dumps({"passed": latest.gates.passed, "retention": retention,
                      "selected": outcome.best.attempt, "pull": latest.read.pull,
                      "calls": len(calls)}, ensure_ascii=False), flush=True)
    if not latest.gates.passed or retention.get("status") != "preserved" or outcome.best.attempt == 1:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
