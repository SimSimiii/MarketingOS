import os
from collections.abc import Generator

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import event
from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine


class DatabaseSettings(BaseSettings):
    """Shared database configuration; importing it needs no platform auth secrets."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./marketingos.db"


def create_app_engine(url: str):
    if url.startswith("sqlite"):
        result = create_engine(
            url, echo=False, connect_args={"check_same_thread": False, "timeout": 30}
        )
    elif os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        # On Lambda, no pool. The database is Aurora Serverless v2, which
        # pauses to zero after a few idle minutes - but only once no
        # connection is open, and a pooled connection held by a frozen Lambda
        # container stays open for as long as AWS keeps the container, which
        # would keep the database billing around the clock. A connection per
        # request costs a few milliseconds inside the VPC. connect_timeout
        # covers a resume from pause, which takes up to about fifteen seconds.
        result = create_engine(
            url, echo=False, poolclass=NullPool, connect_args={"connect_timeout": 25}
        )
    else:
        result = create_engine(url, echo=False)
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
