"""Real-model behavioral checks on preserved drafts; no campaign or sending.

Run from backend with its Python and PYTHONPATH set to backend. Subscription
billing is required. Results are saved beside the original failed brand case.
"""

import asyncio
import argparse
import json
from pathlib import Path

from app.ai.factory import get_ai_provider
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR, get_settings
from app.knowledge.artifacts import KnowledgeArtifacts
from app.marketing.briefs import CampaignBrief
from app.marketing.briefs import EmailBrief
from app.marketing.craft import check_draft
from app.marketing.email_copy import Email
from app.marketing.grounding import ClaimReviewer
from app.marketing.revision import adjustment_review_brief
from app.knowledge.ledger import EvidenceIndex
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import get_prompt_engine

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs/optimization/cleanshot-cold-v30-validation-2026-11-08"


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--additional", action="store_true")
    parser.add_argument("--local", action="store_true")
    options = parser.parse_args()
    assert get_settings().ai_billing != "api", "This check uses configured subscriptions only."
    artifacts = KnowledgeArtifacts.model_validate(json.loads((CASE / "knowledge-final.json").read_text(encoding="utf8"))["artifacts"])
    result = json.loads((CASE / "runs/258d1499-2d6d-431a-9270-f0c309a45661/result.json").read_text(encoding="utf8"))
    brief = CampaignBrief.model_validate(result["result"]["brief"]).emails[0]
    drafts = [Email.model_validate(item) for item in json.loads((CASE / "rejected-drafts.json").read_text(encoding="utf8"))]
    calls = []
    session = ModelSession(get_ai_provider(), get_prompt_engine(PROMPTS_DIR), EventBus(),
                           ModelRouter({"*": "gpt-5.6-sol"}), "claim-review-v31", on_call=calls.append)
    reviewer = ClaimReviewer(session)
    cases = [("original_SCIM", drafts[0], True), ("short_Pro_plan", drafts[1], True),
             ("wrong_billing", drafts[1].model_copy(update={"body": drafts[1].body.replace("billed annually", "billed monthly")}), False),
             ("invented_free_trial", drafts[1].model_copy(update={"body": drafts[1].body + "\n\nYour first 30 days are a free trial with no payment required."}), False)]
    if options.additional:
        cases = [("unsupported_Windows", drafts[1].model_copy(update={"body": drafts[1].body + "\n\nCleanShot also runs natively on Windows."}), False),
                 ("wrong_owner", drafts[1].model_copy(update={"body": drafts[1].body + "\n\nCleanShot is made by MacPaw."}), False),
                 ("excluded_price", drafts[1], False)]
    if options.local:
        local_run = json.loads((CASE / "runs/19107648-aa8d-4e35-982a-bc898befef22/result.json").read_text(encoding="utf8"))
        brief = EmailBrief.model_validate(local_run["assets"][0]["asset_metadata"]["selected_brief"])
        proposal = json.loads((CASE / "revision-proposal-v31.json").read_text(encoding="utf8"))
        brief = adjustment_review_brief(brief, proposal["instruction"])
        cases = [("local_adjustment_current_instruction", Email.model_validate(proposal["email"]), True)]
    output_path = CASE / ("ai-review-v31-local.json" if options.local else
                          "ai-review-v31-additional.json" if options.additional else "ai-review-v31.json")
    output = {"version": "v31-ai-source-review", "billing": "subscription", "cases": []}
    for name, email, expected in cases:
        active_brief = brief.model_copy(deep=True)
        if name == "excluded_price":
            active_brief.forbidden_evidence_ids.append("E18")
            active_brief.steering.avoid.append("Do not include the Pro price in this email.")
        mechanical, _ = check_draft(email, active_brief, artifacts=artifacts,
                                   evidence=EvidenceIndex(artifacts.evidence), previous=[])
        report = mechanical.extend(await reviewer.review(email=email, brief=active_brief, artifacts=artifacts, hints=mechanical))
        output["cases"].append({"name": name, "expected_pass": expected, "passed": report.passed,
                                "matches_expected": report.passed == expected, "report": report.model_dump(mode="json")})
        output["calls"] = len(calls)
        output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf8")
        print(json.dumps({"case": name, "passed": report.passed, "expected": expected,
                          "issues": [i.detail for i in report.blocking]}, ensure_ascii=False), flush=True)
    if not options.additional and not options.local:
        before = len(calls)
        await reviewer.review(email=drafts[0], brief=brief, artifacts=artifacts, hints=mechanical)
        output["identical_draft_reuses_own_review"] = len(calls) == before
    output["estimated_cost_usd"] = sum(c.cost_usd for c in calls)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf8")
    if not all(c["matches_expected"] for c in output["cases"]):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
