"""One isolated tier experiment; never writes application knowledge."""
import asyncio
import json
import sqlite3
import time
from dataclasses import asdict
from pathlib import Path
from uuid import UUID

from app.ai.factory import get_ai_provider
from app.ai.model_router import ModelRouter, ModelTier
from app.core.config import PROMPTS_DIR, get_settings
from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.compiler import _AUDIENCE_DIGEST_CHARS, _AudiencePass
from app.knowledge.corpus import Document, SourceCorpus
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import get_prompt_engine


async def main():
    assert get_settings().ai_billing != "api", "Subscription experiment only"
    case = Path(__file__).resolve().parents[1]
    captured = json.loads((case / "steps/20261025T175014331692Z-capture.json").read_text(encoding="utf-8"))
    artifacts = KnowledgeArtifacts.model_validate(captured["knowledge"]["artifacts"])
    connection = sqlite3.connect("file:marketingos.db?mode=ro", uri=True)
    rows = connection.execute("select id,title,source_url,content,source_type from knowledgedocument where brand_id=? order by created_at desc", ("ab3c12c0642b46c4ac102abae424f516",)).fetchall()
    seen, documents = set(), []
    for id_, title, url, content, source_type in rows:
        if url not in seen:
            seen.add(url)
            documents.append(Document(id=str(UUID(id_)), title=title, source=url or title, content=content, source_type=source_type))
    corpus = SourceCorpus.from_documents(documents)
    calls = []
    session = ModelSession(provider=get_ai_provider(), prompt_engine=get_prompt_engine(PROMPTS_DIR),
        events=EventBus(), model_router=ModelRouter(), execution_id="fathom-audience-balanced-experiment",
        on_call=lambda call: calls.append(asdict(call)))
    started = time.monotonic()
    result = await session.structured(role="knowledge_compiler", tier=ModelTier.BALANCED,
        template="knowledge_audience", variables={"business":artifacts.business.render(),
            "offer":artifacts.offer.render(), "evidence":artifacts.evidence.render(),
            "material":corpus.digest(_AUDIENCE_DIGEST_CHARS)},
        task="Work out who actually buys this, what they are trying to get done, and the real reasons they would not buy.", schema=_AudiencePass)
    value = {"isolated_experiment":True, "tier":"balanced", "duration_seconds":time.monotonic()-started,
        "calls":calls, "audience":result.audience.model_dump(mode="json"),
        "deep_baseline":artifacts.audience.model_dump(mode="json"),
        "note":"No application artifact or campaign updated by this experiment."}
    (case / "audience-balanced-benchmark.json").write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({"seconds":value["duration_seconds"],"calls":len(calls),"segments":len(result.audience.segments)}))


asyncio.run(main())
