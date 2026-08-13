import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal


@dataclass
class ExecutionLogRecord:
    """Structured record of a single agent execution. Shape the future UI consumes."""

    agent_id: str
    execution_id: str
    provider: str
    status: Literal["success", "failed"]
    started_at: datetime
    completed_at: datetime
    duration_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None


def log_execution(logger: logging.Logger, record: ExecutionLogRecord) -> None:
    level = logging.INFO if record.status == "success" else logging.ERROR
    logger.log(level, "agent_execution", extra={"execution": asdict(record)})
