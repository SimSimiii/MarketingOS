"""Operator sign-in: bcrypt passwords, a dedicated JWT, a role ladder.

Deliberately its own implementation rather than a call into `app.auth`. The
two systems share a database and nothing else - a different pepper, a
different signing secret, a different table - so that a token minted for a
customer is not merely *rejected* here but unreadable, and a change to how the
product signs in cannot quietly change how the back-office does.

There is no public signup. The first operator comes from
`scripts/bootstrap_admin.py`; the rest are created by a superadmin.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import bcrypt
import jwt
from app.models.admin import AdminUser
from app.models.enums import AdminRole
from fastapi import Depends, Header, HTTPException, status
from sqlmodel import Session, col, select

from .config import get_admin_settings
from .db import get_session

_ALGORITHM = "HS256"
_TOKEN_TYPE = "admin"
_BCRYPT_ROUNDS = 12

#: Higher is more. Used by `require_role`, which is why the ladder is a dict
#: of levels rather than a set of names: "at least admin" is a question about
#: order, and encoding it as a list of acceptable roles is how a new role gets
#: silently left out of a check.
ROLE_LEVELS: dict[str, int] = {
    AdminRole.SUPPORT: 1,
    AdminRole.ADMIN: 2,
    AdminRole.SUPERADMIN: 3,
}

_UNAUTHENTICATED = HTTPException(
    status.HTTP_401_UNAUTHORIZED,
    "Sign in to continue.",
    headers={"WWW-Authenticate": "Bearer"},
)


# ── Passwords ────────────────────────────────────────────────────────────────


def _peppered(password: str) -> bytes:
    """HMAC first, then bcrypt.

    bcrypt truncates at 72 bytes, so hashing to a fixed 64-char digest keeps a
    long passphrase from being silently shortened - and folding in a pepper
    that lives in the environment means the hashes are useless in a database
    dump on its own.
    """
    pepper = get_admin_settings().admin_pwd_pepper.encode()
    return hmac.new(pepper, password.encode("utf-8"), hashlib.sha256).hexdigest().encode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_peppered(password), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_peppered(password), password_hash.encode())
    except (ValueError, TypeError):
        return False


# ── Tokens ───────────────────────────────────────────────────────────────────


def create_admin_token(admin: AdminUser) -> tuple[str, int]:
    """Return (token, seconds_until_expiry)."""
    settings = get_admin_settings()
    ttl = timedelta(hours=settings.admin_jwt_ttl_hours)
    now = datetime.now(UTC)
    payload = {
        "sub": str(admin.id),
        "email": admin.email,
        "role": str(admin.role),
        "type": _TOKEN_TYPE,
        "iat": now,
        "exp": now + ttl,
    }
    return (
        jwt.encode(payload, settings.admin_jwt_secret, algorithm=_ALGORITHM),
        int(ttl.total_seconds()),
    )


def _decode(token: str) -> dict:
    settings = get_admin_settings()
    try:
        payload = jwt.decode(token, settings.admin_jwt_secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise _UNAUTHENTICATED from exc
    if payload.get("type") != _TOKEN_TYPE:
        raise _UNAUTHENTICATED
    return payload


# ── Dependencies ─────────────────────────────────────────────────────────────


def get_current_admin(
    session: Annotated[Session, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> AdminUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _UNAUTHENTICATED
    payload = _decode(authorization.split(" ", 1)[1].strip())

    try:
        admin_id = UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise _UNAUTHENTICATED from exc

    # Looked up every request rather than trusted from the token: an operator
    # who has just been deactivated should stop being one now, not in twelve
    # hours, and the role in the claim is a snapshot of when they signed in.
    admin = session.exec(select(AdminUser).where(col(AdminUser.id) == admin_id)).first()
    if admin is None or not admin.is_active:
        raise _UNAUTHENTICATED
    return admin


def require_role(minimum: AdminRole):
    """Gate a route behind a minimum role.

    A factory rather than a flag on the route so the requirement is written
    where the route is, in the same words the ladder uses.
    """
    threshold = ROLE_LEVELS[minimum]

    def _check(admin: Annotated[AdminUser, Depends(get_current_admin)]) -> AdminUser:
        if ROLE_LEVELS.get(admin.role, 0) < threshold:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"Requires the '{minimum}' role or higher."
            )
        return admin

    return _check


CurrentAdminDep = Annotated[AdminUser, Depends(get_current_admin)]
