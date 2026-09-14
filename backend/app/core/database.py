from collections.abc import Generator

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine


class DatabaseSettings(BaseSettings):
    """Shared database configuration; importing it needs no platform auth secrets."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./marketingos.db"


def create_app_engine(url: str):
    args = {"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {}
    result = create_engine(url, echo=False, connect_args=args)
    if url.startswith("sqlite"):
        @event.listens_for(result, "connect")
        def configure(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()
    return result


engine = create_app_engine(DatabaseSettings().database_url)


def init_db() -> None:
    """Create tables that don't exist yet. Real schema evolution goes through Alembic."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped DB session."""
    with Session(engine) as session:
        yield session
