from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.enums import AssetType


class GeneratedAsset(SQLModel, table=True):
    """One finished deliverable the user can copy and paste.

    `content` is the ready-to-send text (subject + body for an email, the
    markdown for an article) - never JSON. `asset_metadata` holds the
    structured version for the UI. A run that produces three emails writes
    three rows, ordered by `position`.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    campaign_execution_id: UUID = Field(foreign_key="campaignexecution.id", index=True)
    agent_execution_id: UUID = Field(foreign_key="agentexecution.id", index=True)
    asset_type: AssetType
    title: str
    content: str
    #: The same deliverable as HTML, rendered deterministically from the
    #: structured email (see app.marketing.render_html). Null for assets that
    #: are not emails, and for emails whose render failed - which must never
    #: fail the campaign, since `content` is the deliverable and this is the
    #: presentation of it.
    content_html: str | None = None
    position: int = 0
    asset_metadata: dict | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
