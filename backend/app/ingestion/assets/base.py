from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Asset(BaseModel):
    """Metadata about a binary media file. Assets are never KnowledgeDocuments
    themselves - they must be analyzed by an Analyzer first. This model never
    holds the raw bytes; those exist only transiently in memory during a
    single ingest call (see assets.loader.AssetLoader)."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    source: str
    filename: str
    mime_type: str
    size: int
    checksum: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
