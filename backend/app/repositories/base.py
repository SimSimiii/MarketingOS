from uuid import UUID

from sqlmodel import Session, SQLModel, select


class BaseRepository[ModelT: SQLModel]:
    """Thin CRUD wrapper shared by all repositories. Specific repositories add
    domain queries on top; they never contain business logic."""

    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def get(self, obj_id: UUID) -> ModelT | None:
        return self.session.get(self.model, obj_id)

    def list(self, limit: int = 100, offset: int = 0) -> list[ModelT]:
        statement = select(self.model).offset(offset).limit(limit)
        return list(self.session.exec(statement))

    def update(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def delete(self, obj: ModelT) -> None:
        self.session.delete(obj)
        self.session.commit()
