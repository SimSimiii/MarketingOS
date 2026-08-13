from datetime import UTC, datetime

import pytest

from app.ingestion.documents import RawDocument, SourceType
from app.ingestion.normalizers.default_normalizer import DefaultNormalizer


@pytest.mark.asyncio
async def test_normalize_uses_loader_supplied_title():
    raw = RawDocument(
        content="Some content",
        source="https://example.com",
        source_type=SourceType.WEBSITE,
        fetched_at=datetime.now(UTC),
        metadata={"title": "My Page", "description": "desc"},
    )
    document = await DefaultNormalizer().normalize(raw)

    assert document.title == "My Page"
    assert document.source == SourceType.WEBSITE
    assert document.url == "https://example.com"
    assert document.content_type == "text/markdown"


@pytest.mark.asyncio
async def test_normalize_falls_back_to_first_line_as_title():
    raw = RawDocument(
        content="# Fallback Heading\n\nBody",
        source="notes.md",
        source_type=SourceType.MARKDOWN,
        fetched_at=datetime.now(UTC),
    )
    document = await DefaultNormalizer().normalize(raw)
    assert document.title == "Fallback Heading"


@pytest.mark.asyncio
async def test_normalize_assigns_unique_ids():
    raw = RawDocument(
        content="text",
        source="a.txt",
        source_type=SourceType.PLAIN_TEXT,
        fetched_at=datetime.now(UTC),
    )
    doc1 = await DefaultNormalizer().normalize(raw)
    doc2 = await DefaultNormalizer().normalize(raw)
    assert doc1.id != doc2.id


@pytest.mark.asyncio
async def test_normalize_content_type_by_source():
    cases = [
        (SourceType.JSON, "application/json"),
        (SourceType.PLAIN_TEXT, "text/plain"),
        (SourceType.PDF, "text/plain"),
        (SourceType.DOCX, "text/plain"),
        (SourceType.MARKDOWN, "text/markdown"),
    ]
    for source_type, expected in cases:
        raw = RawDocument(
            content="content",
            source="src",
            source_type=source_type,
            fetched_at=datetime.now(UTC),
        )
        document = await DefaultNormalizer().normalize(raw)
        assert document.content_type == expected, source_type


@pytest.mark.asyncio
async def test_normalize_carries_author_from_metadata():
    raw = RawDocument(
        content="content",
        source="doc.pdf",
        source_type=SourceType.PDF,
        fetched_at=datetime.now(UTC),
        metadata={"author": "Jane Doe"},
    )
    document = await DefaultNormalizer().normalize(raw)
    assert document.author == "Jane Doe"
