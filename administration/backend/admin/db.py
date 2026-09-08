"""The database session, reusing the product's engine.

The back-office is a separate stack with a separate front door, but it is not
a separate database: the customer table it manages is the one the product
writes. Importing `app.core.database.engine` rather than building a second one
means the two can never disagree about which database that is, or about the
connect arguments SQLite needs.
"""

from __future__ import annotations

from collections.abc import Generator

from app.core.database import engine
from sqlmodel import Session


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
