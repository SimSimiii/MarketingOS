from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.ingestion.documents import SourceType


class KnowledgeDocument(SQLModel, table=True):
    """Something the user gave us about their product - their website, a PDF,
    a screenshot - already run through the ingestion engine and normalized.

    Attached to a campaign so one user's product knowledge never leaks into
    another's copy. `campaign_id` is null for reusable library material
    (brand guide, tone of voice) that applies to every campaign.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    #: Material about the business itself - its site, its prices, its past
    #: emails. Every campaign of that brand reads it, which is the point:
    #: a company's own pricing page is not campaign-specific.
    brand_id: UUID | None = Field(default=None, foreign_key="brand.id", index=True)
    campaign_id: UUID | None = Field(default=None, foreign_key="campaign.id", index=True)
    title: str
    source_type: SourceType
    content: str
    source_url: str | None = None
    word_count: int = 0
    document_metadata: dict | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
