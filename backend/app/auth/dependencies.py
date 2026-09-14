"""Resolve bearer credentials; cookie fallback is restricted to safe reads."""

from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlmodel import Session

from app.auth.principal import Principal
from app.auth.tokens import TokenError, decode_access_token
from app.core.config import get_settings
from app.core.database import get_session
from app.models.enums import UserStatus
from app.models.user import User

#: The name the web client stores the access token under. Kept here so the
#: frontend and the API cannot drift apart silently.
ACCESS_TOKEN_COOKIE = "mos_access_token"

_UNAUTHENTICATED = HTTPException(
    status.HTTP_401_UNAUTHORIZED,
    "Sign in to continue.",
    headers={"WWW-Authenticate": "Bearer"},
)


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    return token.strip() or None if scheme.lower() == "bearer" else None


def get_principal(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
    mos_access_token: Annotated[str | None, Cookie()] = None,
) -> Principal:
    """Resolve the caller, or refuse.

    Mutations require an explicit Authorization header. Safe reads may use
    the signed cookie. Query-string tokens are never accepted or logged here.

    An anonymous request is only an error where auth is required. Where it is
    not - a laptop install - it resolves to the unscoped principal, which is
    the single workspace the product had before accounts existed.
    """
    settings = get_settings()
    token = _bearer(authorization)
    if token is None and mos_access_token:
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Use a bearer header for mutations.")
        token = mos_access_token

    if token is None:
        if settings.auth_required:
            raise _UNAUTHENTICATED
        return Principal(user=None, enforced=False)

    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise _UNAUTHENTICATED from exc

    try:
        user_id = UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise _UNAUTHENTICATED from exc

    # One lookup per request, and it earns its keep: it is what makes a
    # suspension take effect now rather than whenever the token expires.
    user = session.get(User, user_id)
    if user is None or payload.get("ver", 0) != user.token_version:
        raise _UNAUTHENTICATED
    if user.status == UserStatus.SUSPENDED:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            user.suspended_reason or "This account has been suspended.",
        )
    return Principal(user=user, enforced=settings.auth_required)


def get_current_user(principal: Annotated[Principal, Depends(get_principal)]) -> User:
    """For routes that need an actual account - changing a password, reading
    "me". Single-user mode has no account, so these are the routes it cannot
    call, and 401 is the honest answer."""
    if principal.user is None:
        raise _UNAUTHENTICATED
    return principal.user


PrincipalDep = Annotated[Principal, Depends(get_principal)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
