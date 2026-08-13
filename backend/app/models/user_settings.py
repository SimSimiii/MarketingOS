from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class UserSettings(SQLModel, table=True):
    """Singleton-style settings row (MVP is single-user, no auth yet)."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    company_name: str | None = None
    brand_voice: str | None = None
    default_ai_provider: str = "claude"
    default_model: str = "claude-sonnet-4-6"
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
