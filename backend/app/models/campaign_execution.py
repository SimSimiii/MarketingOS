from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.enums import ExecutionStatus


class CampaignExecution(SQLModel, table=True):
    """One orchestrated run of the agent pipeline for a given Campaign."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    campaign_id: UUID = Field(foreign_key="campaign.id", index=True)
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, index=True)
    result: dict | None = Field(default=None, sa_column=Column(JSON))
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    #: Campaign-wide totals, summed across every model call made during this
    #: run. Populated on finalize; see CampaignOrchestrator.
    #:
    #: `total_input_tokens` counts every input token the run consumed, cached
    #: input included - which is what quota is actually spent on. Runs recorded
    #: before this column existed carry only the uncached fraction, so a
    #: historical row may read implausibly low beside a recent one.
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    #: The cached share of the input above, kept separately so the cost of a
    #: run can be explained rather than just stated.
    total_cache_read_tokens: int = 0
    estimated_cost_usd: float = 0.0
