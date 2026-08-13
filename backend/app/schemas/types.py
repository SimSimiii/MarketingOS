from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator


def _as_utc(value: datetime) -> datetime:
    """Tag a naive datetime as UTC.

    Every timestamp is written with `datetime.now(UTC)`, but SQLite (and any
    column declared without `timezone=True`) hands it back naive. Serialized
    that way it reaches the browser as "2026-08-03T19:31:43" with no marker,
    and `new Date(...)` reads that as *local* time - so every displayed time
    was silently off by the viewer's UTC offset. The value really is UTC;
    this just says so.
    """
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


#: A datetime that always serializes with an explicit UTC offset.
UtcDatetime = Annotated[datetime, AfterValidator(_as_utc)]
