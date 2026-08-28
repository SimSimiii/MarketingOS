from collections.abc import Collection
from uuid import UUID

from sqlmodel import col, func, select

from app.models.campaign_execution import CampaignExecution
from app.models.enums import ExecutionStatus
from app.repositories.base import BaseRepository


class CampaignExecutionRepository(BaseRepository[CampaignExecution]):
    model = CampaignExecution

    def list_by_campaign(self, campaign_id: UUID) -> list[CampaignExecution]:
        statement = (
            select(CampaignExecution)
            .where(CampaignExecution.campaign_id == campaign_id)
            .order_by(CampaignExecution.created_at.desc())
        )
        return list(self.session.exec(statement))

    def list_by_campaigns(self, campaign_ids: Collection[UUID]) -> list[CampaignExecution]:
        """The same rows for a set of campaigns, in one query.

        The plural exists because the forecast compares a campaign against
        every other run the user has made on the same preset, and asking
        `list_by_campaign` once per campaign is the same N+1 that
        `latest_by_campaign` below was written to avoid.
        """
        if not campaign_ids:
            return []
        statement = (
            select(CampaignExecution)
            .where(col(CampaignExecution.campaign_id).in_(list(campaign_ids)))
            .order_by(CampaignExecution.created_at.desc())
        )
        return list(self.session.exec(statement))

    def list_running(self) -> list[CampaignExecution]:
        """Every run currently in flight, newest first - what the live
        dashboard watches. Read from the database rather than the in-process
        registry so the answer is the same one every other view of the
        execution gives."""
        statement = (
            select(CampaignExecution)
            .where(CampaignExecution.status == ExecutionStatus.RUNNING)
            .order_by(col(CampaignExecution.started_at).desc())
        )
        return list(self.session.exec(statement))

    def latest_by_campaign(self) -> dict[UUID, tuple[ExecutionStatus, object]]:
        """Most recent run per campaign, as {campaign_id: (status, created_at)}.

        One grouped query for the whole list - the campaigns index needs a
        run indicator per row, and asking per campaign would be a classic
        N+1.
        """
        newest = (
            select(
                col(CampaignExecution.campaign_id).label("campaign_id"),
                func.max(col(CampaignExecution.created_at)).label("created_at"),
            )
            .group_by(col(CampaignExecution.campaign_id))
            .subquery()
        )
        statement = select(CampaignExecution).join(
            newest,
            (col(CampaignExecution.campaign_id) == newest.c.campaign_id)
            & (col(CampaignExecution.created_at) == newest.c.created_at),
        )
        return {
            execution.campaign_id: (execution.status, execution.created_at)
            for execution in self.session.exec(statement)
        }
