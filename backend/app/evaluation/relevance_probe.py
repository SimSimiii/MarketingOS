"""Small semantic probe: three existing BlindReader calls, no campaign/research.

Default --dry-run is free. --run spends subscription quota (three reader calls).
"""
import argparse
import asyncio
import json
from pathlib import Path

from app.ai.factory import get_ai_provider
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR
from app.marketing.email_copy import Email
from app.marketing.reader import BlindReader
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import get_prompt_engine


def cases():
    data = json.loads(Path(__file__).with_name("relevance_cases.json").read_text(encoding="utf-8"))
    observed = data["observed_email"]
    subject, rest = observed.split("\n", 1)
    preview, rest = rest.strip().split("\n", 1)
    headline, body = rest.strip().split("\n", 1)
    body = body.strip().removeprefix("Hi there,").strip()
    body, _ = body.split("Create your first agent", 1)
    base = {"position": 1, "greeting": "Hi there,", "sign_off": "the orqAgent team"}
    original = Email(
        **base, subject=subject, preview_text=preview.removeprefix("Preview: "),
        headline=headline, body=body.strip(), call_to_action="Create your first agent",
        postscript="The free plan needs no card. One agent is enough to test this.",
    )
    adapted_body = data["adapted_body"].removeprefix("Hi there,").strip()
    adapted_body = adapted_body.removesuffix("The orqAgent team").strip()
    adapted = Email(
        **base, subject="Inspect a call before your first launch", preview_text="",
        body=adapted_body, call_to_action="Create one agent and inspect a run",
    )
    return [
        ("observed-first-feature", data["audience"], original),
        ("adapted-first-feature", data["audience"], adapted),
        ("observed-production", data["production_audience"], original),
    ]


async def run():
    session = ModelSession(
        provider=get_ai_provider(), prompt_engine=get_prompt_engine(PROMPTS_DIR),
        events=EventBus(), model_router=ModelRouter(), execution_id="relevance-probe",
    )
    reader = BlindReader(session)
    results = []
    for name, audience, email in cases():
        panel = await reader.read(email, [audience])
        results.append({"case": name, "panel": panel.model_dump(mode="json")})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("eval/relevance.json"))
    args = parser.parse_args()
    if not args.run or args.dry_run:
        print(json.dumps([{"case": n, "audience": a, "email": e.model_dump()} for n, a, e in cases()], indent=2))
        return
    print("Spending quota: three blind-reader calls; no campaign or research.")
    results = asyncio.run(run())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
