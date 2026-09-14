from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, and_, col, or_, select

from app.auth.principal import Principal
from app.auth.scope import owned
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.knowledge_document import KnowledgeDocument
from app.repositories.base import BaseRepository


class KnowledgeDocumentRepository(BaseRepository[KnowledgeDocument]):
    model = KnowledgeDocument

    def __init__(self, session: Session, principal: Principal | None = None) -> None:
        super().__init__(session)
        self.principal = principal

    def _scoped(self, statement):
        if self.principal is None or self.principal.user is None:
            return statement
        brands = owned(select(Brand.id), Brand, self.principal)
        campaigns = owned(select(Campaign.id), Campaign, self.principal)
        library = owned(select(KnowledgeDocument.id), KnowledgeDocument, self.principal).where(
            col(KnowledgeDocument.brand_id).is_(None),
            col(KnowledgeDocument.campaign_id).is_(None),
        )
        return statement.where(or_(
            col(KnowledgeDocument.campaign_id).in_(campaigns),
            and_(col(KnowledgeDocument.campaign_id).is_(None),
                 col(KnowledgeDocument.brand_id).in_(brands)),
            col(KnowledgeDocument.id).in_(library),
        ))

    def get(self, obj_id: UUID) -> KnowledgeDocument | None:
        return self.session.exec(self._scoped(select(self.model).where(self.model.id == obj_id))).first()

    def list(self, limit: int = 100, offset: int = 0) -> list[KnowledgeDocument]:
        return list(self.session.exec(self._scoped(select(self.model)).order_by(
            self.model.created_at.desc(), self.model.id
        ).offset(offset).limit(limit)))

    def list_for_campaign(self, campaign_id: UUID, limit: int | None = None,
                          offset: int = 0) -> list[KnowledgeDocument]:
        """Knowledge attached to this campaign, plus campaign-agnostic library
        material (brand guide, tone of voice). Never another campaign's
        product - that is how one client's copy ends up describing another's."""
        campaign = self.session.get(Campaign, campaign_id)
        if campaign is None:
            return []
        statement = select(KnowledgeDocument).where(
            or_(
                col(KnowledgeDocument.campaign_id) == campaign_id,
                and_(
                    col(KnowledgeDocument.campaign_id).is_(None),
                    col(KnowledgeDocument.brand_id).is_(None),
                    col(KnowledgeDocument.owner_id) == campaign.owner_id,
                ),
            )
        )
        return list(self.session.exec(self._scoped(statement).order_by(
            self.model.created_at.desc(), self.model.id).offset(offset).limit(limit)))

    def list_by_campaign(self, campaign_id: UUID) -> list[KnowledgeDocument]:
        statement = select(KnowledgeDocument).where(
            col(KnowledgeDocument.campaign_id) == campaign_id
        )
        return list(self.session.exec(self._scoped(statement)))

    def list_for_brand(self, brand_id: UUID, limit: int | None = None,
                       offset: int = 0) -> list[KnowledgeDocument]:
        """Everything about this business: material filed under the brand
        itself, plus whatever was uploaded to any of its campaigns. A pricing
        page dropped into one campaign is a fact about the company, not about
        that campaign, and every later campaign should be able to read it."""
        statement = select(KnowledgeDocument).where(
            or_(
                col(KnowledgeDocument.brand_id) == brand_id,
                col(KnowledgeDocument.campaign_id).in_(
                    select(Campaign.id).where(Campaign.brand_id == brand_id)
                ),
            )
        )
        return list(self.session.exec(self._scoped(statement).order_by(
            self.model.created_at.desc(), self.model.id).offset(offset).limit(limit)))

    def list_by_brand_only(self, brand_id: UUID) -> list[KnowledgeDocument]:
        statement = select(KnowledgeDocument).where(
            col(KnowledgeDocument.brand_id) == brand_id,
            col(KnowledgeDocument.campaign_id).is_(None),
        )
        return list(self.session.exec(self._scoped(statement)))
