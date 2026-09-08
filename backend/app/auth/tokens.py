"""Token minting and reading.

Two different kinds, for two different jobs:

- The **access token** is a signed JWT nobody stores. It is checked by
  signature alone, which is what keeps a database query off the front of every
  request - and the reason it is short-lived, since a revoked account keeps
  working until it expires.
- The **refresh token** is opaque random bytes whose *hash* is a row
  (app.models.user.UserSession). It is presented rarely and must be killable,
  so the tradeoff runs the other way.
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt

from app.core.config import get_settings

_ALGORITHM = "HS256"

#: Distinguishes the two JWT families this app signs with the same secret.
#: Without it an access token would be accepted anywhere any token is, which
#: is how a token minted for one purpose ends up authorising another.
ACCESS_TOKEN_TYPE = "access"


class TokenError(Exception):
    """The token was absent, malformed, expired, or not ours."""


def create_access_token(
    user_id: UUID, email: str, role: str, plan: str, *, ttl_minutes: int | None = None
) -> tuple[str, int]:
    """Return (token, seconds_until_expiry).

    The lifetime is returned rather than left for the client to parse out of
    the payload: a client that decodes a JWT to find out when to refresh is a
    client that will one day trust a claim it should have verified.
    """
    settings = get_settings()
    ttl = timedelta(minutes=ttl_minutes or settings.access_token_ttl_minutes)
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "plan": plan,
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + ttl,
        "jti": uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM), int(ttl.total_seconds())


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise TokenError("Wrong token type")
    return payload


def new_refresh_token() -> tuple[str, str]:
    """Return (raw_token, token_hash). The raw value is never stored."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    """Keyed with the pepper rather than a bare SHA-256.

    A bare digest of 48 random bytes is not guessable either, but keying it
    means the stored value is worthless in a database that leaves without the
    process environment - the same property the password hashes have.
    """
    pepper = get_settings().password_pepper.encode()
    return hmac.new(pepper, raw.encode(), hashlib.sha256).hexdigest()


def refresh_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=get_settings().refresh_token_ttl_days)
