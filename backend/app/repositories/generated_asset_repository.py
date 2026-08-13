from uuid import UUID

from sqlmodel import select

from app.models.generated_asset import GeneratedAsset
from app.repositories.base import BaseRepository


class GeneratedAssetRepository(BaseRepository[GeneratedAsset]):
    model = GeneratedAsset

    def list_by_execution(self, campaign_execution_id: UUID) -> list[GeneratedAsset]:
        statement = select(GeneratedAsset).where(
            GeneratedAsset.campaign_execution_id == campaign_execution_id
        )
        return list(self.session.exec(statement))
