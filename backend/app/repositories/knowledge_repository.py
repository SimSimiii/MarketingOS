from uuid import UUID

from sqlmodel import col, or_, select

from app.models.knowledge_document import KnowledgeDocument
from app.repositories.base import BaseRepository


class KnowledgeDocumentRepository(BaseRepository[KnowledgeDocument]):
    model = KnowledgeDocument

    def list_for_campaign(self, campaign_id: UUID) -> list[KnowledgeDocument]:
        """Knowledge attached to this campaign, plus campaign-agnostic library
        material (brand guide, tone of voice). Never another campaign's
        product - that is how one client's copy ends up describing another's."""
        statement = select(KnowledgeDocument).where(
            or_(
                col(KnowledgeDocument.campaign_id) == campaign_id,
                col(KnowledgeDocument.campaign_id).is_(None),
            )
        )
        return list(self.session.exec(statement))

    def list_by_campaign(self, campaign_id: UUID) -> list[KnowledgeDocument]:
        statement = select(KnowledgeDocument).where(
            col(KnowledgeDocument.campaign_id) == campaign_id
        )
        return list(self.session.exec(statement))

    def list_for_brand(self, brand_id: UUID) -> list[KnowledgeDocument]:
        """Everything about this business: material filed under the brand
        itself, plus whatever was uploaded to any of its campaigns. A pricing
        page dropped into one campaign is a fact about the company, not about
        that campaign, and every later campaign should be able to read it."""
        statement = select(KnowledgeDocument).where(
            col(KnowledgeDocument.brand_id) == brand_id
        )
        return list(self.session.exec(statement))

    def list_by_brand_only(self, brand_id: UUID) -> list[KnowledgeDocument]:
        statement = select(KnowledgeDocument).where(
            col(KnowledgeDocument.brand_id) == brand_id,
            col(KnowledgeDocument.campaign_id).is_(None),
        )
        return list(self.session.exec(statement))
