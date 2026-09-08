from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class UserSettings(SQLModel, table=True):
    """One account's preferences: default provider, default model, voice.

    Was a singleton row when the product had one user. It is now keyed by
    `user_id`, and the null key is still meaningful: it is the row single-user
    mode reads and writes, so a local install keeps the settings it had.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID | None = Field(default=None, foreign_key="user.id", index=True, unique=True)
    company_name: str | None = None
    brand_voice: str | None = None
    default_ai_provider: str = "claude"
    default_model: str = "claude-sonnet-4-6"
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
