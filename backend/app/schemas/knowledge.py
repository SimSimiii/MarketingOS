from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ingestion.documents import SourceType
from app.knowledge.base import KnowledgeBase, KnowledgeEntry, KnowledgeShelf
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


class KnowledgeShelfRead(BaseModel):
    """One category of the knowledge base, as the browser receives it.

    Counts are computed server-side rather than left to the client because
    they are also what the strategist reads, and two implementations of "how
    many facts are strong enough to lead an email" is one too many.
    """

    category: str
    label: str
    blurb: str
    buyer_question: str
    sells_by: str
    when_empty: str
    count: int
    headline_count: int
    entries: list[KnowledgeEntry]

    @classmethod
    def from_shelf(cls, shelf: KnowledgeShelf) -> "KnowledgeShelfRead":
        return cls(
            category=str(shelf.category),
            label=shelf.label,
            blurb=shelf.blurb,
            buyer_question=shelf.buyer_question,
            sells_by=shelf.sells_by,
            when_empty=shelf.when_empty,
            count=shelf.count,
            headline_count=shelf.headline_count,
            entries=shelf.entries,
        )


class KnowledgeBaseRead(BaseModel):
    """The whole classified knowledge base for one business.

    Shipped in full - shelves and entries together - rather than paginated. A
    large compile is a few hundred entries of a couple of hundred bytes each,
    which is smaller than one of the source documents it was distilled from,
    and having all of it client-side is what makes filtering and search
    instant instead of a round trip per keystroke.
    """

    brand_id: UUID | None = None
    campaign_id: UUID | None = None
    version: int
    compiled_at: UtcDatetime | None = None
    total: int
    citable_total: int
    headline_total: int
    shelves: list[KnowledgeShelfRead]
    #: Gaps the compiler could not close, carried through so the page can say
    #: what to upload next rather than only what is missing.
    open_questions: list[str]

    @classmethod
    def from_base(
        cls,
        base: KnowledgeBase,
        brand_id: UUID | None = None,
        campaign_id: UUID | None = None,
    ) -> "KnowledgeBaseRead":
        return cls(
            brand_id=brand_id,
            campaign_id=campaign_id,
            version=base.version,
            compiled_at=base.compiled_at,
            total=base.total,
            citable_total=base.citable_total,
            headline_total=base.headline_total,
            shelves=[KnowledgeShelfRead.from_shelf(shelf) for shelf in base.shelves],
            open_questions=base.open_questions,
        )
