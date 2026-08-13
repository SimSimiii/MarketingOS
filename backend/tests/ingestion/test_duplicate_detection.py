from datetime import UTC, datetime

import pytest

from app.ingestion.chunkers.heading_chunker import HeadingChunker
from app.ingestion.documents import KnowledgeDocument, SourceType
from app.ingestion.exceptions import DuplicateDocumentError
from app.ingestion.loaders.registry import default_registry
from app.ingestion.normalizers.default_normalizer import DefaultNormalizer
from app.ingestion.pipeline import IngestionPipeline, default_cleaners
from app.ingestion.store.in_memory_store import InMemoryKnowledgeStore


def make_document(content_hash: str) -> KnowledgeDocument:
    return KnowledgeDocument(
        title="Doc",
        source=SourceType.PLAIN_TEXT,
        created_at=datetime.now(UTC),
        content="same content",
        content_type="text/plain",
        metadata={"content_hash": content_hash},
    )


@pytest.mark.asyncio
async def test_store_rejects_duplicate_content_hash():
    store = InMemoryKnowledgeStore()
    await store.add_document(make_document("same-hash"))

    with pytest.raises(DuplicateDocumentError) as exc_info:
        await store.add_document(make_document("same-hash"))

    assert exc_info.value.details["existing_id"]


@pytest.mark.asyncio
async def test_store_allows_different_content_hashes():
    store = InMemoryKnowledgeStore()
    await store.add_document(make_document("hash-a"))
    await store.add_document(make_document("hash-b"))  # should not raise

    assert len(await store.list_documents()) == 2


def make_pipeline(store: InMemoryKnowledgeStore) -> IngestionPipeline:
    return IngestionPipeline(
        loaders=default_registry(),
        normalizer=DefaultNormalizer(),
        cleaners=default_cleaners(),
        chunker=HeadingChunker(),
        store=store,
    )


@pytest.mark.asyncio
async def test_pipeline_ingest_is_idempotent_for_identical_content():
    store = InMemoryKnowledgeStore()
    pipeline = make_pipeline(store)
    text = "# Same Document\n\nIdentical content every time."

    first = await pipeline.ingest(text, source_type=SourceType.MARKDOWN)
    second = await pipeline.ingest(text, source_type=SourceType.MARKDOWN)

    assert first.id == second.id
    assert len(await store.list_documents()) == 1


@pytest.mark.asyncio
async def test_pipeline_ingest_stores_distinct_content_separately():
    store = InMemoryKnowledgeStore()
    pipeline = make_pipeline(store)

    first = await pipeline.ingest("# Doc One\n\nContent one.", source_type=SourceType.MARKDOWN)
    second = await pipeline.ingest("# Doc Two\n\nContent two.", source_type=SourceType.MARKDOWN)

    assert first.id != second.id
    assert len(await store.list_documents()) == 2
