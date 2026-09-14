from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class LinkedInRun(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brand.id", index=True)
    kind: str
    state: str = "running"
    # Unique while running, NULL after completion: one paid job per brand.
    active_key: str | None = Field(default=None, unique=True)
    request: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    result: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    error: str = ""
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
