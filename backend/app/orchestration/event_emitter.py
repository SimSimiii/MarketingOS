import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.models.enums import LogLevel
from app.models.execution_log import ExecutionLog
from app.orchestration.live_broker import broker
from app.repositories.execution_log_repository import ExecutionLogRepository

logger = logging.getLogger("marketingos.orchestration")

#: Payload keys the emitter owns. Extra data from a caller is merged at the
#: top level (so a client reads `event.input_tokens`, not
#: `event.data.input_tokens`), and must not quietly overwrite these.
_RESERVED_KEYS = frozenset(
    {"type", "execution_id", "agent_id", "step", "level", "message", "at"}
)


class ExecutionEventEmitter:
    """The single funnel every live event goes through.

    One call both writes an ExecutionLog row and publishes the same payload
    to the SSE broker. Keeping them together is the point: the live stream
    and what a reloaded page replays from the database are then the same
    data by construction, instead of two code paths that drift until the
    timeline disagrees with what the user watched happen.

    Everything here is fire-and-forget from the run's perspective - an
    emitter failure must never take a campaign down with it, so persistence
    errors are swallowed after the broadcast has gone out.
    """

    def __init__(self, logs: ExecutionLogRepository, execution_id: UUID) -> None:
        self._logs = logs
        self._execution_id = execution_id
        #: The role turn the run is currently on. Events raised deeper in the
        #: stack - the model session announcing a call, say - have no way to
        #: know it, yet the UI groups everything by step. The observer sets it
        #: once per turn and every event emitted under it inherits it.
        self.current_step: int | None = None

    def emit(
        self,
        event_type: str,
        message: str,
        *,
        level: LogLevel = LogLevel.INFO,
        agent_id: str | None = None,
        step: int | None = None,
        agent_execution_id: UUID | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        step = step if step is not None else self.current_step
        payload: dict[str, Any] = {
            "type": event_type,
            "execution_id": str(self._execution_id),
            "agent_id": agent_id,
            "step": step,
            "level": level.value,
            "message": message,
            "at": datetime.now(UTC).isoformat(),
        }
        payload.update({k: v for k, v in (data or {}).items() if k not in _RESERVED_KEYS})

        live_event = broker.publish(self._execution_id, payload)
        try:
            self._logs.append(
                ExecutionLog(
                    campaign_execution_id=self._execution_id,
                    agent_execution_id=agent_execution_id,
                    agent_id=agent_id,
                    step=step,
                    event_type=event_type,
                    data=payload,
                    sequence=live_event.id,
                    level=level,
                    message=message,
                )
            )
        except Exception:
            # A log write must never take a campaign down with it - the
            # broadcast already went out, and the run has real work in flight.
            logger.warning("could not persist execution log line %r", event_type, exc_info=True)
