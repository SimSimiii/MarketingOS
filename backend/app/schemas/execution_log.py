from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import LogLevel
from app.schemas.types import UtcDatetime


class ExecutionLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_execution_id: UUID | None
    agent_execution_id: UUID | None
    #: Which role emitted this line ("email_writer", "blind_reader", ...).
    agent_id: str | None = None
    #: The director step it belongs to, correlating a delegation with the run
    #: it produced.
    step: int | None = None
    event_type: str | None = None
    level: LogLevel
    message: str
    created_at: UtcDatetime


class ExecutionTimeline(BaseModel):
    """Everything a client needs to render a run it did not watch live.

    `events` are the exact payloads that were broadcast over SSE, replayed
    from the database in order, so a page that opened late or reloaded
    mid-run rebuilds the same timeline instead of starting blank.
    `last_event_id` is where the live stream should resume from.
    """

    execution_id: UUID
    events: list[dict] = []
    last_event_id: int = 0
    is_running: bool = False
