"""One explicitly selected closed-world profile call; never writes brand data."""
import asyncio
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "backend"))

from sqlmodel import Session

from app.ai.model_router import ModelRouter
from app.ai.openai_provider import OpenAIProvider
from app.core.config import PROMPTS_DIR
from app.core.database import engine
from app.knowledge.compiler import KnowledgeCompiler
from app.knowledge.store import ArtifactScope, ArtifactStore, build_corpus, fingerprint_documents
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import get_prompt_engine

ROOT = Path(__file__).resolve().parents[1]
key = sys.argv[1]
if key not in {"cabaia", "systeme"}:
    raise SystemExit("Only the two preregistered comparison cases are allowed")
directory = ROOT / "model-comparison" / key
directory.mkdir(parents=True, exist_ok=True)
if (directory / "input.json").exists():
    raise SystemExit("Attempt already recorded; inspect it instead of rerunning")


def save(name, value):
    (directory / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


class CapturedProvider(OpenAIProvider):
    async def generate(self, request):
        save("request.json", request.model_dump(mode="json"))
        return await super().generate(request)


async def main():
    case = json.loads((ROOT / key / "case.json").read_text(encoding="utf-8"))
    with Session(engine) as db:
        store = ArtifactStore(db)
        scope = ArtifactScope(brand_id=UUID(case["brand_id"]))
        docs = store.source_documents(scope)
        corpus = build_corpus(docs)
        baseline = store.load(scope)
        save("input.json", {"brand_id": case["brand_id"], "source_fingerprint": fingerprint_documents(docs),
                            "profile_digest_sha256": hashlib.sha256(corpus.digest(40000).encode()).hexdigest(),
                            "baseline_fingerprint": baseline.fingerprint if baseline else None,
                            "baseline_version": baseline.version if baseline else None,
                            "model": "gpt-5.6-sol", "kind": "diagnostic_profile_only"})
        if baseline is None or baseline.fingerprint != fingerprint_documents(docs):
            raise RuntimeError("A successful compilation of these exact inputs is required first")
        save("baseline-profile.json", {"business": baseline.artifacts.business.model_dump(mode="json"),
                                       "offer": baseline.artifacts.offer.model_dump(mode="json")})
    calls = []
    session = ModelSession(provider=CapturedProvider(), prompt_engine=get_prompt_engine(PROMPTS_DIR),
                           events=EventBus(), model_router=ModelRouter(overrides={"knowledge_compiler": "gpt-5.6-sol"}),
                           execution_id=f"diagnostic-profile:{key}", on_call=lambda call: calls.append(asdict(call)))
    try:
        profile = await KnowledgeCompiler(session)._profile(corpus)
        save("candidate-profile.json", profile.model_dump(mode="json"))
    except Exception as exc:
        save("error.json", {"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        save("calls.json", calls)
    print(json.dumps({"case": key, "directory": str(directory), "calls": len(calls)}), flush=True)


asyncio.run(main())
