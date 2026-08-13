from sqlmodel import col, select

from app.models.brand import Brand
from app.repositories.base import BaseRepository


class BrandRepository(BaseRepository[Brand]):
    model = Brand

    def list_all(self) -> list[Brand]:
        return list(self.session.exec(select(Brand).order_by(col(Brand.created_at).desc())))

    def find_by_name(self, name: str) -> Brand | None:
        return self.session.exec(select(Brand).where(col(Brand.name) == name)).first()
