import os
import time
from collections.abc import Callable, Generator

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import event
from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine


class DatabaseSettings(BaseSettings):
    """Shared database configuration; importing it needs no platform auth secrets."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./marketingos.db"


#: How long a Lambda waits out an Aurora Serverless resume. A paused cluster
#: does not hold the first connection until it is ready - it closes it - and
#: resumes in about fifteen seconds. Six tries three seconds apart cover that
#: inside API Gateway's thirty-second limit.
RESUME_ATTEMPTS = 6
RESUME_WAIT_SECONDS = 3.0


def connect_with_retry[T](
    connect: Callable[[], T],
    retry_on: type[BaseException] | tuple[type[BaseException], ...],
    *,
    attempts: int = RESUME_ATTEMPTS,
    wait: float = RESUME_WAIT_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call `connect`, trying again on `retry_on` until `attempts` run out."""
    for attempt in range(1, attempts + 1):
        try:
            return connect()
        except retry_on:
            if attempt == attempts:
                raise
            sleep(wait)
    raise AssertionError("unreachable")


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
        # request costs a few milliseconds inside the VPC. A resume from pause
        # is waited out by retrying the connection - see connect_with_retry.
        result = create_engine(
            url, echo=False, poolclass=NullPool, connect_args={"connect_timeout": 10}
        )

        @event.listens_for(result, "do_connect")
        def _wait_out_a_resume(dialect, _record, cargs, cparams):
            return connect_with_retry(
                lambda: dialect.connect(*cargs, **cparams),
                dialect.loaded_dbapi.OperationalError,
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
