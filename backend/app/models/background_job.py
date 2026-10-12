from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class BackgroundJob(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brand.id", index=True)
    owner_id: UUID | None = Field(default=None, foreign_key="user.id", index=True)
    action: str
    category: str
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    status: dict = Field(default_factory=dict, sa_column=Column(JSON))
    active: bool = True
    claimed: bool = False
    model_calls: int = 0
    model_tokens: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
