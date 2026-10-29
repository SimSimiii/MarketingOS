"""Independently refetch saved research URLs; never feed this review to the API."""
import asyncio
import json
import sys
from pathlib import Path

directory = Path(__file__).resolve().parent
repo = directory.parents[2]
sys.path.insert(0, str(repo / "backend"))
from app.knowledge.corpus import fold
from app.market.audience_research import FixedURLFetcher, LocatedSource

research = json.loads((directory / "steps/20261020T011352411287Z-capture.json").read_text(encoding="utf-8"))["research"]


async def main():
    result = await FixedURLFetcher().fetch([
        LocatedSource(url=source["requested_url"], tier=source["tier"], venue=source["venue"])
        for source in research["sources"]
    ])
    by_url = {url: source for source in result.sources for url in [source.requested_url, source.final_url]}
    by_id = {source["id"]: by_url.get(source["requested_url"]) for source in research["sources"]}
    quotes = set()

    def collect(value):
        if isinstance(value, dict):
            if value.get("source_id") and value.get("quote"):
                quotes.add((value["source_id"], value["quote"]))
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(research)
    missing = [{"source": sid, "quote": quote} for sid, quote in sorted(quotes)
               if by_id.get(sid) and fold(quote) not in fold(by_id[sid].content)]
    review = {"refetched_sources": len(result.sources), "unique_quotations": len(quotes),
              "unavailable_sources": [sid for sid, source in by_id.items() if source is None],
              "quotation_mismatches": missing,
              "sources": [{"url": source.final_url, "published_date": str(source.published_date),
                           "hash_matches_capture": source.content_hash == original["content_hash"]}
                          for original in research["sources"]
                          if (source := by_url.get(original["requested_url"]))],
              "failures": [failure.model_dump() for failure in result.failures]}
    (directory / "research-quotation-review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in review.items() if key != "sources"}))


asyncio.run(main())
