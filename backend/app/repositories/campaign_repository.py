from uuid import UUID

from sqlmodel import Session, col, select

from app.auth.principal import Principal
from app.auth.scope import may_read, owned
from app.models.campaign import Campaign
from app.models.enums import CampaignStatus
from app.repositories.base import BaseRepository


class CampaignRepository(BaseRepository[Campaign]):
    """Campaigns, narrowed to the account that asked for them.

    A campaign is the second owned root - see app.auth.scope for why it is not
    enough to scope brands alone. `principal` is optional so the background
    runner, which has no caller, can still load the campaign it is running.
    """

    model = Campaign

    def __init__(self, session: Session, principal: Principal | None = None) -> None:
        super().__init__(session)
        self.principal = principal

    def _scoped(self, statement):
        return statement if self.principal is None else owned(statement, Campaign, self.principal)

    def get(self, obj_id: UUID) -> Campaign | None:
        campaign = super().get(obj_id)
        if campaign is None or self.principal is None:
            return campaign
        return campaign if may_read(campaign, self.principal) else None

    def list_active(self) -> list[Campaign]:
        statement = (
            select(Campaign)
            .where(Campaign.status == CampaignStatus.ACTIVE)
            .order_by(Campaign.created_at.desc())
        )
        return list(self.session.exec(self._scoped(statement)))

    def list_all(self) -> list[Campaign]:
        statement = select(Campaign).order_by(Campaign.created_at.desc())
        return list(self.session.exec(self._scoped(statement)))

    def list_by_brand(self, brand_id: UUID) -> list[Campaign]:
        """Every campaign for one business, newest first - how a run finds
        what earlier campaigns for the same brand learned."""
        statement = (
            select(Campaign)
            .where(col(Campaign.brand_id) == brand_id)
            .order_by(Campaign.created_at.desc())
        )
        return list(self.session.exec(self._scoped(statement)))
