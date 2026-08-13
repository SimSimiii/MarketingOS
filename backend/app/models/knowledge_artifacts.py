from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class KnowledgeArtifactSet(SQLModel, table=True):
    """One compiled version of everything the system knows about a business.

    Versions are kept rather than overwritten: a campaign records which set it
    was written against, so its copy stays explainable after the company
    changes its pricing page. `source_fingerprint` is what makes recompiling
    skippable - it covers the documents that went in, so an unchanged corpus
    reuses the artifacts instead of paying for them again.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    #: Exactly one of these is set. A brand-scoped set is shared by every
    #: campaign of that brand; a campaign-scoped one belongs to a one-off.
    brand_id: UUID | None = Field(default=None, foreign_key="brand.id", index=True)
    campaign_id: UUID | None = Field(default=None, foreign_key="campaign.id", index=True)
    version: int = 1
    source_fingerprint: str = Field(default="", index=True)
    #: Serialized app.knowledge.artifacts.KnowledgeArtifacts.
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
