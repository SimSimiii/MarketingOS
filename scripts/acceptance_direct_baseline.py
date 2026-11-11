"""One direct-writing comparison with the same compiled knowledge and writer model.

Run from backend; the case must already contain a persisted campaign_id.
Never calls a model outside ModelSession, never edits a campaign or sends mail.
"""
import asyncio
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


async def main(case_path):
    from app.ai.factory import get_ai_provider
    from app.ai.model_router import ModelRouter, ModelTier
    from app.marketing.policy import resolve_policy
    from app.runtime.events import EventBus, ModelCallRetried
    from app.runtime.model_session import ModelSession
    from app.runtime.prompt_engine import PromptEngine

    case = json.loads(case_path.read_text(encoding="utf-8"))
    folder = case_path.parent / "direct-baseline"
    folder.mkdir(exist_ok=False)

    def get(route):
        with urlopen(case["api_base"] + "/api/" + route, timeout=30) as response:
            return json.load(response)

    campaign = get("campaigns/" + case["campaign_id"])
    knowledge = get("brands/" + case["brand_id"] + "/knowledge")
    market = get("market/" + case["brand_id"])
    audience_context = {}
    if audience := campaign.get("audience_segment"):
        query = urlencode({"segment": audience})
        audience_context = {
            "research": get("market/" + case["brand_id"] + "/audience/research/latest?" + query),
            "relevance": get("market/" + case["brand_id"] + "/audience/relevance/status?" + query),
        }
    policy_data = campaign.get("policy") or {}
    policy = resolve_policy(policy_data.get("preset"), policy_data)
    overrides = {**policy.model_overrides, **(campaign.get("model_overrides") or {})}
    model = ModelRouter(overrides).resolve("email_writer", ModelTier.DEEP)
    material = {
        "request": campaign["request"],
        "audience": campaign.get("audience_segment"),
        "intent": campaign.get("intent"),
        "sender_name": campaign.get("sender_name"),
        "sender_role": campaign.get("sender_role"),
        "fixed_cta_url": campaign.get("cta_url"),
        "brand_knowledge": knowledge["artifacts"],
        "audience_context": audience_context,
        "market_positioning": market.get("positioning"),
        "content_choices": campaign.get("steering"),
    }
    save(folder / "input.json", material)
    instruction = (
        "You are an expert email copywriter. Fulfil the user's request using the supplied "
        "brand knowledge and audience. Choose a specific useful supported argument and a "
        "proportionate next step. Preserve source conditions; never invent facts, results, "
        "urgency or recipient history. Use only a documented destination for links. "
        "Write polished emails for ordinary brand review and export. Return each email "
        "with Subject, Preview text, body, call to action with its URL, and sign-off. "
        "Return the emails only, no commentary or analysis."
    )
    (folder / "system-prompt.txt").write_text(instruction, encoding="utf-8")
    events = EventBus()
    retries = []
    events.subscribe(ModelCallRetried, lambda event: retries.append(asdict(event)))
    session = ModelSession(get_ai_provider(), PromptEngine(ROOT / "backend/prompts"), events,
                           ModelRouter({"*": model}), execution_id="direct-" + case["campaign_id"])
    start = time.monotonic()
    save(folder / "state.json", {"status": "running", "model": model})
    try:
        text = await session.text(role="email_writer", tier=ModelTier.DEEP,
                                  system_prompt=instruction,
                                  task=json.dumps(material, ensure_ascii=False))
        (folder / "email.txt").write_text(text, encoding="utf-8")
        save(folder / "state.json", {"status": "completed", "model": model,
                                     "seconds": time.monotonic() - start,
                                     "usage": asdict(session.usage), "retries": retries})
        print(case_path.parent.name, "direct baseline completed", len(session.usage.calls), "call(s)")
    except Exception as error:
        save(folder / "state.json", {"status": "failed", "model": model, "error": str(error),
                                     "seconds": time.monotonic() - start,
                                     "usage": asdict(session.usage), "retries": retries})
        raise


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1]).resolve()))
