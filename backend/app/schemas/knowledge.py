from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ingestion.documents import SourceType
from app.schemas.types import UtcDatetime


class KnowledgeSourceCreate(BaseModel):
    """Add knowledge from a URL or from pasted text.

    Files (PDF, DOCX, screenshots) go through the upload endpoint instead.
    """

    campaign_id: UUID | None = None
    #: File the material under the business rather than one campaign, so every
    #: campaign for that brand reads it. See app.knowledge.store.ArtifactScope.
    brand_id: UUID | None = None
    title: str | None = None
    url: str | None = None
    content: str | None = None
    #: For a URL: read the pages it links to as well, not just that one page.
    #: On by default because a home page rarely contains a checkable fact.
    crawl: bool = True
    max_pages: int = Field(default=12, ge=1, le=40)

    @model_validator(mode="after")
    def check_source_payload(self) -> "KnowledgeSourceCreate":
        if not self.url and not self.content:
            raise ValueError("Provide either `url` (a web page) or `content` (pasted text)")
        if self.url and self.content:
            raise ValueError("Provide `url` or `content`, not both")
        return self


class KnowledgeDocumentSummary(BaseModel):
    """A document as it appears in lists - metadata only.

    Deliberately excludes `content`: an ingested PDF or website can be
    hundreds of kilobytes, and listing every document would ship all of it to
    the browser for a table that displays none of it. Fetch a single document
    by id when the text itself is actually needed.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID | None
    brand_id: UUID | None = None
    title: str
    source_type: SourceType
    source_url: str | None
    word_count: int
    created_at: UtcDatetime


class KnowledgeDocumentRead(KnowledgeDocumentSummary):
    """A single document, including the extracted text."""

    content: str
