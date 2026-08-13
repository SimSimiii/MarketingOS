from datetime import UTC, datetime

import pytest

from app.ingestion.chunkers.fixed_size_chunker import FixedSizeChunker
from app.ingestion.chunkers.heading_chunker import HeadingChunker
from app.ingestion.documents import KnowledgeDocument, SourceType


def make_document(content: str) -> KnowledgeDocument:
    return KnowledgeDocument(
        title="Doc",
        source=SourceType.MARKDOWN,
        created_at=datetime.now(UTC),
        content=content,
        content_type="text/markdown",
        metadata={"content_hash": "abc123"},
    )


def test_fixed_size_chunker_splits_by_size_with_overlap():
    document = make_document("a" * 250)
    chunker = FixedSizeChunker(chunk_size=100, overlap=20)
    chunks = chunker.chunk(document)

    assert len(chunks) == 4  # step=80: 0,80,160,240
    assert all(c.document_id == document.id for c in chunks)
    assert [c.index for c in chunks] == [0, 1, 2, 3]


def test_fixed_size_chunker_preserves_document_metadata():
    document = make_document("hello world " * 20)
    chunks = FixedSizeChunker(chunk_size=50, overlap=5).chunk(document)
    assert chunks[0].metadata["content_hash"] == "abc123"
    assert chunks[0].metadata["chunk_index"] == 0


def test_fixed_size_chunker_rejects_overlap_larger_than_size():
    with pytest.raises(ValueError, match="overlap"):
        FixedSizeChunker(chunk_size=10, overlap=10)


def test_fixed_size_chunker_empty_content_returns_no_chunks():
    document = make_document("")
    assert FixedSizeChunker().chunk(document) == []


def test_heading_chunker_splits_on_headings():
    content = "# Intro\nIntro text\n\n## Details\nDetail text\n\n## More\nMore text"
    document = make_document(content)
    chunks = HeadingChunker().chunk(document)

    assert len(chunks) == 3
    assert chunks[0].metadata["heading"] == "Intro"
    assert chunks[1].metadata["heading"] == "Details"
    assert chunks[2].metadata["heading"] == "More"
    assert "Detail text" in chunks[1].content


def test_heading_chunker_keeps_preamble_without_heading():
    content = "Some preamble text\n\n# First Heading\nBody"
    document = make_document(content)
    chunks = HeadingChunker().chunk(document)

    assert "heading" not in chunks[0].metadata
    assert "Some preamble text" in chunks[0].content
    assert chunks[1].metadata["heading"] == "First Heading"


def test_heading_chunker_preserves_document_metadata():
    document = make_document("# Heading\nBody text")
    chunks = HeadingChunker().chunk(document)
    assert chunks[0].metadata["content_hash"] == "abc123"
