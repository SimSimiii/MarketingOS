"""Two focused writer probes using saved inputs and the subscription CLI only.

Run from backend with PYTHONPATH set to that directory. Requires --run;
without it no model is called.
This is a manual behavioural experiment, not a scripted test or a campaign.
"""

import argparse
import asyncio
import json
from dataclasses import asdict, fields
from pathlib import Path

from app.ai.model_router import ModelRouter
from app.ai.openai_provider import OpenAIProvider
from app.core.config import PROMPTS_DIR, get_settings
from app.knowledge.artifacts import KnowledgeArtifacts
from app.marketing.briefs import CampaignBrief
from app.marketing.email_copy import Email
from app.marketing.render_html import BrandStyle, text_alternative
from app.marketing.request import CampaignRequest
from app.marketing.writer import EmailWriter
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import PromptEngine

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "docs/optimization/marketingos-self/gpt-enriched"
OUT = ROOT / "docs/reviews/recipient-activity-probe-2026-10-16"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


async def run():
    assert not get_settings().credit_billing_enabled, "Local probe must not create credit charges"
    source = read(CASE / "runs/62cbd16d-85ab-44a7-93c7-d4a6cb56fd6f/result.json")
    artifacts = KnowledgeArtifacts.model_validate(read(CASE / "knowledge.json")["artifacts"])
    campaign = CampaignBrief.model_validate(source["result"]["brief"])
    original = read(CASE / "campaign.json")
    request = CampaignRequest(**{
        field.name: original[field.name]
        for field in fields(CampaignRequest) if field.name in original
    })
    previous = [Email.model_validate(source["assets"][0]["asset_metadata"])]
    calls = []
    session = ModelSession(
        provider=OpenAIProvider(), prompt_engine=PromptEngine(PROMPTS_DIR),
        events=EventBus(), model_router=ModelRouter(overrides={"*": "gpt-5.6-sol"}),
        execution_id="local-recipient-activity-probe", on_call=calls.append,
    )
    OUT.mkdir(exist_ok=True)
    for name, condition in [
        ("unknown-progress", ""),
        ("confirmed-completion", " This second email is sent ONLY to recipients who have "
         "completed a first MarketingOS campaign and have a finished report to inspect."),
    ]:
        current = CampaignRequest(**{**asdict(request), "request": request.request + condition})
        print(f"Writing {name} through subscription CLI", flush=True)
        email = await EmailWriter(session).draft(
            brief=campaign.emails[1], campaign=campaign, request=current,
            artifacts=artifacts, previous=previous,
        )
        (OUT / f"{name}.json").write_text(email.model_dump_json(indent=2), encoding="utf-8")
        (OUT / f"{name}.txt").write_text(
            text_alternative(email, BrandStyle(cta_url=request.cta_url or "")), encoding="utf-8",
        )
        print(f"Saved {name}", flush=True)
    (OUT / "usage.json").write_text(json.dumps({
        "provider": "OpenAIProvider subscription CLI", "api_requests": False,
        "model": "gpt-5.6-sol", "calls": [asdict(call) for call in calls],
        "scope": "Two standalone writer probes; not an end-to-end campaign or API invoice.",
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    if parser.parse_args().run:
        asyncio.run(run())
    else:
        print("Dry run: two writer probes, saved corpus, no research. --run uses CLI quota.")
