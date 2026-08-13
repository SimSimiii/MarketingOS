from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.enums import CampaignStatus


class Campaign(SQLModel, table=True):
    """What the user wants, in their own words, plus the context that helps
    write it.

    `request` is the contract the run is measured against - e.g. "write me 3
    emails that make people buy my product". Everything else is optional
    context; the product's website and images live in KnowledgeDocument.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    #: The business this campaign is for. Optional: without it the campaign
    #: compiles its own knowledge and keeps it to itself, which is right for a
    #: one-off and wasteful for the fifth campaign of the same product.
    brand_id: UUID | None = Field(default=None, foreign_key="brand.id", index=True)
    name: str
    request: str
    product_description: str
    product_url: str | None = None
    target_market: str | None = None
    goals: str | None = None
    status: CampaignStatus = Field(default=CampaignStatus.ACTIVE, index=True)
    archived_at: datetime | None = None
    #: Serialized ExecutionPolicy overrides (see app.marketing.policy) plus
    #: the preset name it was built from - {"preset": "fast", ...fields}.
    #: None means "use the balanced preset with no overrides".
    policy: dict | None = Field(default=None, sa_column=Column(JSON))
    #: Per-role model overrides keyed by role id, or "*" for all of them - see
    #: app.ai.model_router.ModelRouter. Distinct from `policy` so a user can
    #: pick a model for one role without adopting a whole preset.
    model_overrides: dict[str, str] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
