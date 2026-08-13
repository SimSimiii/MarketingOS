from datetime import UTC, datetime

import pytest

from app.ingestion.documents import KnowledgeDocument, SourceType
from app.ingestion.exceptions import DocumentNotFoundError
from app.ingestion.store.in_memory_store import InMemoryKnowledgeStore


def make_document(title: str, content: str, content_hash: str) -> KnowledgeDocument:
    return KnowledgeDocument(
        title=title,
        source=SourceType.PLAIN_TEXT,
        created_at=datetime.now(UTC),
        content=content,
        content_type="text/plain",
        metadata={"content_hash": content_hash},
    )


@pytest.mark.asyncio
async def test_add_then_get_document():
    store = InMemoryKnowledgeStore()
    document = make_document("Doc", "content", "hash1")
    await store.add_document(document)

    fetched = await store.get_document(document.id)
    assert fetched == document


@pytest.mark.asyncio
async def test_get_missing_document_raises():
    store = InMemoryKnowledgeStore()
    with pytest.raises(DocumentNotFoundError):
        await store.get_document("missing-id")


@pytest.mark.asyncio
async def test_list_documents_returns_all():
    store = InMemoryKnowledgeStore()
    doc1 = make_document("Doc1", "content1", "hash1")
    doc2 = make_document("Doc2", "content2", "hash2")
    await store.add_document(doc1)
    await store.add_document(doc2)

    documents = await store.list_documents()
    assert {d.id for d in documents} == {doc1.id, doc2.id}


@pytest.mark.asyncio
async def test_remove_document():
    store = InMemoryKnowledgeStore()
    document = make_document("Doc", "content", "hash1")
    await store.add_document(document)

    await store.remove_document(document.id)
    with pytest.raises(DocumentNotFoundError):
        await store.get_document(document.id)


@pytest.mark.asyncio
async def test_remove_missing_document_raises():
    store = InMemoryKnowledgeStore()
    with pytest.raises(DocumentNotFoundError):
        await store.remove_document("missing-id")


@pytest.mark.asyncio
async def test_search_matches_keywords_in_title_and_content():
    store = InMemoryKnowledgeStore()
    await store.add_document(make_document("Marketing Guide", "widgets and gadgets", "hash1"))
    await store.add_document(make_document("Cooking Guide", "recipes and food", "hash2"))

    results = await store.search("widgets")
    assert len(results) == 1
    assert results[0].title == "Marketing Guide"


@pytest.mark.asyncio
async def test_search_ranks_more_matching_terms_higher():
    store = InMemoryKnowledgeStore()
    high = make_document("High Match", "widgets gadgets widgets", "hash1")
    low = make_document("Low Match", "widgets only", "hash2")
    await store.add_document(high)
    await store.add_document(low)

    results = await store.search("widgets gadgets")
    assert [d.id for d in results] == [high.id, low.id]


@pytest.mark.asyncio
async def test_search_no_matches_returns_empty_list():
    store = InMemoryKnowledgeStore()
    await store.add_document(make_document("Doc", "content", "hash1"))
    assert await store.search("nonexistent") == []
