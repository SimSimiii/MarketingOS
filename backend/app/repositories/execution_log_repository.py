from uuid import UUID

from sqlmodel import col, select

from app.models.enums import LogLevel
from app.models.execution_log import ExecutionLog
from app.repositories.base import BaseRepository


class ExecutionLogRepository(BaseRepository[ExecutionLog]):
    model = ExecutionLog

    def list_by_execution(
        self,
        campaign_execution_id: UUID,
        agent_id: str | None = None,
        levels: list[LogLevel] | None = None,
        after_sequence: int | None = None,
        limit: int | None = None,
    ) -> list[ExecutionLog]:
        """One run's lines, oldest first - the order they happened in.

        `agent_id` narrows to a single role's lane (what the live view's
        per-agent log panel asks for), `levels` drops the DEBUG progress
        chatter when the caller only wants the story, and `after_sequence`
        fetches just what is new since the client's last known position.
        """
        statement = select(ExecutionLog).where(
            ExecutionLog.campaign_execution_id == campaign_execution_id
        )
        if agent_id is not None:
            statement = statement.where(ExecutionLog.agent_id == agent_id)
        if levels:
            statement = statement.where(col(ExecutionLog.level).in_(levels))
        if after_sequence is not None:
            statement = statement.where(ExecutionLog.sequence > after_sequence)
        statement = statement.order_by(col(ExecutionLog.created_at), col(ExecutionLog.sequence))
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.session.exec(statement))

    def list_recent(self, limit: int = 200) -> list[ExecutionLog]:
        statement = select(ExecutionLog).order_by(col(ExecutionLog.created_at).desc()).limit(limit)
        return list(self.session.exec(statement))
