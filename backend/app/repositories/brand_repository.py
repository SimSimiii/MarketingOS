from uuid import UUID

from sqlmodel import Session, col, select

from app.auth.principal import Principal
from app.auth.scope import may_read, owned
from app.models.brand import Brand
from app.repositories.base import BaseRepository


class BrandRepository(BaseRepository[Brand]):
    """Brands, narrowed to the account that asked for them.

    The tenancy check lives here rather than in the routes because a brand is
    one of the two roots everything else hangs off (see app.auth.scope): a
    route that forgets it would not leak a brand, it would leak that brand's
    knowledge, market and campaigns. One place to get right.

    `principal` is optional so the background campaign runner - which has no
    request and no caller - can keep reading rows by id.
    """

    model = Brand

    def __init__(self, session: Session, principal: Principal | None = None) -> None:
        super().__init__(session)
        self.principal = principal

    def get(self, obj_id: UUID) -> Brand | None:
        """None rather than a 403 for someone else's brand.

        The route turns this into "Brand not found", which is the right answer
        to give: a 403 confirms the id exists, and an id that exists is worth
        guessing at.
        """
        brand = super().get(obj_id)
        if brand is None or self.principal is None:
            return brand
        return brand if may_read(brand, self.principal) else None

    def list_all(self) -> list[Brand]:
        statement = select(Brand).order_by(col(Brand.created_at).desc())
        if self.principal is not None:
            statement = owned(statement, Brand, self.principal)
        return list(self.session.exec(statement))

    def find_by_name(self, name: str) -> Brand | None:
        statement = select(Brand).where(col(Brand.name) == name)
        if self.principal is not None:
            statement = owned(statement, Brand, self.principal)
        return self.session.exec(statement).first()
