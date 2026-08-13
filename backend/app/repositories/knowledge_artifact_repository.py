from uuid import UUID

from sqlmodel import col, select

from app.models.knowledge_artifacts import KnowledgeArtifactSet
from app.repositories.base import BaseRepository


class KnowledgeArtifactRepository(BaseRepository[KnowledgeArtifactSet]):
    model = KnowledgeArtifactSet

    def latest_for_brand(self, brand_id: UUID) -> KnowledgeArtifactSet | None:
        return self._latest(col(KnowledgeArtifactSet.brand_id) == brand_id)

    def latest_for_campaign(self, campaign_id: UUID) -> KnowledgeArtifactSet | None:
        return self._latest(col(KnowledgeArtifactSet.campaign_id) == campaign_id)

    def list_for_brand(self, brand_id: UUID) -> list[KnowledgeArtifactSet]:
        statement = (
            select(KnowledgeArtifactSet)
            .where(col(KnowledgeArtifactSet.brand_id) == brand_id)
            .order_by(col(KnowledgeArtifactSet.version).desc())
        )
        return list(self.session.exec(statement))

    def _latest(self, condition) -> KnowledgeArtifactSet | None:
        statement = (
            select(KnowledgeArtifactSet)
            .where(condition)
            .order_by(col(KnowledgeArtifactSet.version).desc())
        )
        return self.session.exec(statement).first()
