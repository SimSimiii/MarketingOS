"""Targeted paid role probe; run from backend, never touches the application DB.

Three role calls measure the discovered warranty overclaim, not a campaign score.
"""
import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from app.ai.factory import get_ai_provider
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR, get_settings
from app.knowledge.artifacts import KnowledgeArtifacts
from app.marketing.briefs import CampaignBrief
from app.marketing.critic import ConversionCritic
from app.marketing.email_copy import Email
from app.marketing.gates import GateReport
from app.marketing.reader import PanelRead
from app.marketing.request import CampaignRequest
from app.marketing.writer import EmailWriter
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import get_prompt_engine

ROOT = Path(__file__).resolve().parent


async def main():
    assert get_settings().ai_billing != "api", "Subscription probe only"
    result = json.loads((ROOT / "runs/22f5e0eb-591f-40be-b453-a1369b1c23fd/result.json").read_text(encoding="utf-8"))
    knowledge = json.loads((ROOT / "knowledge.json").read_text(encoding="utf-8"))
    artifacts = KnowledgeArtifacts.model_validate(knowledge["artifacts"])
    campaign = CampaignBrief.model_validate(result["result"]["brief"])
    brief = campaign.emails[2]
    emails = [Email.model_validate(asset["asset_metadata"]) for asset in result["assets"]]
    session = ModelSession(
        provider=get_ai_provider(), prompt_engine=get_prompt_engine(PROMPTS_DIR),
        events=EventBus(), model_router=ModelRouter({"*": "gpt-5.6-sol"}),
        execution_id="probe-ifixit-warranty-v5",
    )
    output = {"scope": "targeted role probe, not a scored full campaign", "knowledge_version": knowledge["version"]}

    def save():
        output["calls"] = [asdict(call) for call in session.usage.calls]
        (ROOT / "warranty-probe.json").write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    critic = ConversionCritic(session)
    old = await critic.critique(
        email=emails[2], brief=brief, campaign=campaign, artifacts=artifacts,
        read=PanelRead(), gates=GateReport(),
    )
    output["old_draft_critique"] = old.model_dump()
    save()
    print("Old warranty critique captured", flush=True)
    revised = await EmailWriter(session).revise(
        draft=emails[2], brief=brief, campaign=campaign, artifacts=artifacts,
        request=CampaignRequest(name="iFixit pilot", request=result["result"]["report"]["request"],
                                cta_url=campaign.fixed_cta_url),
        previous=emails[:2], gates=GateReport(), read=PanelRead(), critique_notes=old.render(),
    )
    output["revised_email"] = revised.model_dump()
    save()
    print("Revised warranty email captured", flush=True)
    new = await critic.critique(
        email=revised, brief=brief, campaign=campaign, artifacts=artifacts,
        read=PanelRead(), gates=GateReport(),
    )
    output["revised_critique"] = new.model_dump()
    save()
    print("Targeted probe finished", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
