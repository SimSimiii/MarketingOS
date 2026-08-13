from uuid import UUID

from sqlmodel import col, select

from app.models.campaign import Campaign
from app.models.enums import CampaignStatus
from app.repositories.base import BaseRepository


class CampaignRepository(BaseRepository[Campaign]):
    model = Campaign

    def list_active(self) -> list[Campaign]:
        statement = (
            select(Campaign)
            .where(Campaign.status == CampaignStatus.ACTIVE)
            .order_by(Campaign.created_at.desc())
        )
        return list(self.session.exec(statement))

    def list_all(self) -> list[Campaign]:
        statement = select(Campaign).order_by(Campaign.created_at.desc())
        return list(self.session.exec(statement))

    def list_by_brand(self, brand_id: UUID) -> list[Campaign]:
        """Every campaign for one business, newest first - how a run finds
        what earlier campaigns for the same brand learned."""
        statement = (
            select(Campaign)
            .where(col(Campaign.brand_id) == brand_id)
            .order_by(Campaign.created_at.desc())
        )
        return list(self.session.exec(statement))
