from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.enums import ExecutionStatus


class AgentExecution(SQLModel, table=True):
    """A single agent's run within a CampaignExecution. Ordered by sequence_order."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    campaign_execution_id: UUID = Field(foreign_key="campaignexecution.id", index=True)
    agent_id: str = Field(index=True)
    agent_name: str
    sequence_order: int
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING)
    input_data: dict | None = Field(default=None, sa_column=Column(JSON))
    output_data: dict | None = Field(default=None, sa_column=Column(JSON))
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    #: Which model actually ran this step (see app.ai.model_router.ModelRouter).
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    #: Input that was written to, and read from, the prompt cache. With the
    #: Claude Code CLI this is the overwhelming majority of a step's input -
    #: `input_tokens` alone reports single digits for a 30,000-character
    #: prompt - so a row without these columns cannot say what the step cost.
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    #: What this step cost, provider-reported where the provider said.
    cost_usd: float = 0.0
    duration_ms: float = 0.0
    #: Which run of this agent, within this campaign, this is (1 = first).
    #: Lets the UI show "retry 2/3" instead of just another roster row.
    attempt: int = 1
