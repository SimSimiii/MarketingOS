"""Real bounded HTTP crawl from the homepage only. No DB write or model call."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from app.ingestion.loaders.site_crawler import SiteCrawler
from app.knowledge.compiler import _readings
from app.knowledge.corpus import Document, SourceCorpus


async def main():
    documents = await SiteCrawler().crawl("https://buffer.com/")
    corpus = SourceCorpus.from_documents([
        Document(id=str(i), title=str(d.metadata.get("title", "")), content=d.content, source=d.source)
        for i, d in enumerate(documents)
    ])
    plan = _readings(corpus, 14000, 240000)
    result = {
        "kind": "Real HTTP coverage check, no model call, not a knowledge recompilation",
        "homepage_only_input": "https://buffer.com/", "pages": len(documents),
        "characters": sum(len(d.content) for d in documents),
        "evidence_batches_if_compiled": len(plan.batches), "unread_characters": plan.unread,
        "documents": [{"source_url": d.source, "metadata": d.metadata, "content": d.content}
                      for d in documents],
    }
    path = Path(__file__).parent / "crawl-after-fix.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({**{k:v for k,v in result.items() if k != "documents"},
                      "urls": [d.source for d in documents]}, ensure_ascii=False, indent=2))


asyncio.run(main())
