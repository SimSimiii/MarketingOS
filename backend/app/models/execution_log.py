from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.enums import LogLevel


class ExecutionLog(SQLModel, table=True):
    """One thing that happened during a campaign run - and, at the same time,
    one event of its live stream.

    Every line the orchestrator emits is both persisted here and published to
    the SSE broker in a single call (see
    app.orchestration.event_emitter.ExecutionEventEmitter). That is why the
    row carries the structured fields a live client needs rather than only a
    message: it lets a page that opened late, or reloaded mid-run, rebuild
    exactly the timeline the stream would have shown it.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    campaign_execution_id: UUID | None = Field(
        default=None, foreign_key="campaignexecution.id", index=True
    )
    agent_execution_id: UUID | None = Field(
        default=None, foreign_key="agentexecution.id", index=True
    )
    #: Which role this line belongs to ("email_writer", "blind_reader", ...).
    #: Set from the moment work starts, unlike `agent_execution_id`, which only
    #: exists once the role's turn has finished and its row has been written -
    #: so this is what lets the UI attribute live lines to a lane.
    agent_id: str | None = Field(default=None, index=True)
    #: The role turn this line happened in. One writer draft, one cold read or
    #: one critique per step - which is also the unit that costs money.
    step: int | None = Field(default=None)
    #: Machine-readable kind ("agent_completed", "review", "gates", ...);
    #: `message` stays the human sentence for the flat activity log.
    event_type: str | None = Field(default=None, index=True)
    #: The exact payload broadcast over SSE for this line. Stored verbatim so
    #: the replay endpoint hands a reconnecting client the same shape the
    #: stream did, with no second mapping to keep in sync.
    data: dict | None = Field(default=None, sa_column=Column(JSON))
    #: Position of this line in the live stream (the SSE event id it was sent
    #: with). It is what lets a client load its history over HTTP and then
    #: resume the stream at exactly the right place - without it, catching up
    #: means either missing what happened during the handover or replaying it
    #: twice. 0 for rows written before the live stream had ids.
    sequence: int = Field(default=0)
    level: LogLevel = Field(default=LogLevel.INFO)
    message: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
