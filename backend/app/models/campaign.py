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
    #: Where the call to action points. The writer never knows this - it is
    #: told so, and told to write the words that go on the link rather than
    #: the link itself - so it is asked for here instead. Without it (and
    #: without a brand website to fall back on) a branded email renders its
    #: CTA as a styled link rather than a button, because a button that goes
    #: nowhere costs a real reader a click and the sender the reply.
    cta_url: str | None = None
    #: The name of an audience segment from the brand's demand map, chosen by
    #: the user for this campaign. Optional, and the whole point of mapping
    #: demand: with it set, the run is written to the buyer the market says
    #: would answer rather than to the one the company's website describes.
    #: A plain name rather than an id - see app.models.market.ProspectRow.
    audience_segment: str | None = None
    #: Optional qualified company target from the brand's prospect list. A
    #: campaign without one stays audience-level; a company-specific campaign
    #: cannot silently name a company that has never been qualified.
    prospect_id: UUID | None = Field(default=None, foreign_key="prospectrow.id", index=True)
    #: Who the emails are from - a person and their job, e.g. "Marco" and
    #: "founder". Optional, and worth asking for: without it every email in
    #: the campaign is signed by a team rather than a human, which is a
    #: signature readers have learned to read as a broadcast.
    sender_name: str | None = None
    sender_role: str | None = None
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
