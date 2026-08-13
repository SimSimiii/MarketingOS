from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SourceType(StrEnum):
    """Supported ingestion sources. Adding a new one here plus a Loader (and,
    only if needed, a Normalizer) is the entire extension surface."""

    WEBSITE = "website"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"
    PDF = "pdf"
    DOCX = "docx"
    JSON = "json"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class RawDocument(BaseModel):
    """What a Loader produces: unprocessed content plus whatever the loader
    could tell about it. Deliberately generic - no per-source fields, so the
    Normalizer stage never has to branch on source_type."""

    content: str
    source: str
    source_type: SourceType
    fetched_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    """A slice of a KnowledgeDocument's content, produced by a Chunker."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    document_id: str
    index: int
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeDocument(BaseModel):
    """The canonical representation every future agent reads from, regardless
    of which source it came from."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    title: str
    source: SourceType
    url: str | None = None
    author: str | None = None
    language: str | None = None
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    content: str
    content_type: str
    chunks: list[Chunk] = Field(default_factory=list)
    #: Set when this document was produced from an Asset (image/video/audio)
    #: rather than a text RawDocument. References an Asset stored separately
    #: in an AssetStore - never a raw binary blob.
    asset_id: str | None = None
