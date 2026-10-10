"""Atomic password-attempt limits shared by API instances and process restarts.

Identity limits do not trust X-Forwarded-For. The deployment must additionally
limit traffic per client at its trusted edge; an identity counter is not a
bandwidth limiter and deliberately does not lock everybody behind one proxy.
"""

import hashlib
import hmac
import math
import time

from sqlalchemy import case, delete, or_
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session

from app.models.auth_rate_limit import AuthRateLimit

PASSWORD_ATTEMPTS = 12
WINDOW_SECONDS = 300


class AuthThrottledError(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__("Too many authentication attempts. Wait a few minutes and try again.")
        self.retry_after = retry_after


def password_attempt(
    session: Session, *, email: str, namespace: str, pepper: str, now: float | None = None,
) -> None:
    """Consume one attempt before password hashing, even for an unknown identity.

    Commit separately from authentication: rolling back a failed login must
    not roll back its attempt. Call before any account mutation in the session.
    All attempts count, including successful ones, so another valid credential
    cannot reset the counter and race password guesses against it.
    """
    current = time.time() if now is None else now
    window = int(current // WINDOW_SECONDS) * WINDOW_SECONDS
    key = hmac.new(
        pepper.encode(), f"{namespace}\0{email.strip().lower()}".encode(), hashlib.sha256,
    ).hexdigest()
    table = AuthRateLimit.__table__
    dialect = session.get_bind().dialect.name
    if dialect == "sqlite":
        insert = sqlite_insert
    elif dialect == "postgresql":
        insert = postgres_insert
    else:
        raise RuntimeError("Password-attempt limits require SQLite or PostgreSQL.")
    statement = insert(table).values(key=key, window_start=window, attempts=1)
    statement = statement.on_conflict_do_update(
        index_elements=[table.c.key],
        set_={
            "window_start": window,
            "attempts": case(
                (table.c.window_start != window, 1), else_=table.c.attempts + 1,
            ),
        },
        where=or_(table.c.window_start != window, table.c.attempts < PASSWORD_ATTEMPTS),
    ).returning(table.c.key)
    accepted = session.execute(statement).first() is not None
    # Expired identities do not accumulate forever, including invalid emails.
    session.execute(delete(table).where(table.c.window_start < window - 86400))
    session.commit()
    if not accepted:
        raise AuthThrottledError(max(1, math.ceil(window + WINDOW_SECONDS - current)))
