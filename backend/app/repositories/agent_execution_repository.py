from uuid import UUID

from sqlmodel import select

from app.models.agent_execution import AgentExecution
from app.repositories.base import BaseRepository


class AgentExecutionRepository(BaseRepository[AgentExecution]):
    model = AgentExecution

    def list_by_execution(self, campaign_execution_id: UUID) -> list[AgentExecution]:
        statement = (
            select(AgentExecution)
            .where(AgentExecution.campaign_execution_id == campaign_execution_id)
            .order_by(AgentExecution.sequence_order)
        )
        return list(self.session.exec(statement))
