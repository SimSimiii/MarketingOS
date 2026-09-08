"""Sign-up, sign-in, refresh, sign-out.

The tokens go back in the body *and* as cookies. The body is what a script or
a native client uses; the cookies are what makes server-rendered pages work,
because a Next.js server component has the request's cookies and does not have
whatever the browser put in `localStorage`. Both carry the same token, so
neither is a second way in.
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Header, HTTPException, Request, Response, status
from sqlmodel import Session, col, select

from app.api.deps import SessionDep
from app.auth import service
from app.auth.dependencies import ACCESS_TOKEN_COOKIE, CurrentUserDep
from app.core.config import get_settings
from app.models.user import User, UserSession
from app.schemas.auth import (
    AuthConfigRead,
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    SessionRead,
    TokenResponse,
    UserRead,
)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_TOKEN_COOKIE = "mos_refresh_token"
#: The refresh cookie is only ever read by /refresh and /logout below, so
#: scoping it to this router keeps it off every other request.
_REFRESH_COOKIE_PATH = "/api/auth"


def _set_cookies(response: Response, tokens: service.IssuedTokens) -> None:
    settings = get_settings()
    secure = settings.is_production
    response.set_cookie(
        ACCESS_TOKEN_COOKIE,
        tokens.access_token,
        max_age=tokens.expires_in,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        REFRESH_TOKEN_COOKIE,
        tokens.refresh_token,
        max_age=settings.refresh_token_ttl_days * 24 * 3600,
        httponly=True,
        secure=secure,
        samesite="lax",
        path=_REFRESH_COOKIE_PATH,
    )


def _clear_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(REFRESH_TOKEN_COOKIE, path=_REFRESH_COOKIE_PATH)


def _client_ip(request: Request) -> str | None:
    # X-Forwarded-For is client-controlled, and behind API Gateway or
    # CloudFront the left-most entry is the one the edge saw. Stored for a
    # human reading an incident, never used to decide anything.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return request.client.host if request.client else None


def _token_response(tokens: service.IssuedTokens) -> TokenResponse:
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        user=UserRead.model_validate(tokens.user),
    )


def _issue(
    session: Session, user: User, request: Request, response: Response, user_agent: str | None
) -> TokenResponse:
    tokens = service.issue_tokens(
        session, user, user_agent=user_agent, ip_address=_client_ip(request)
    )
    _set_cookies(response, tokens)
    return _token_response(tokens)


@router.get("/config", response_model=AuthConfigRead)
def auth_config() -> AuthConfigRead:
    """Unauthenticated on purpose: the sign-in page has to render before
    anybody has a token, and it needs to know whether to offer signup."""
    settings = get_settings()
    return AuthConfigRead(
        auth_required=settings.auth_required,
        allow_public_signup=settings.allow_public_signup,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    data: RegisterRequest,
    session: SessionDep,
    request: Request,
    response: Response,
    user_agent: Annotated[str | None, Header()] = None,
) -> TokenResponse:
    try:
        user = service.register(
            session,
            email=data.email,
            password=data.password,
            full_name=data.full_name,
            company_name=data.company_name,
        )
    except service.SignupClosedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except service.EmailTakenError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return _issue(session, user, request, response, user_agent)


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    session: SessionDep,
    request: Request,
    response: Response,
    user_agent: Annotated[str | None, Header()] = None,
) -> TokenResponse:
    try:
        user = service.authenticate(session, email=data.email, password=data.password)
    except service.AccountSuspendedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except service.AuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return _issue(session, user, request, response, user_agent)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    data: RefreshRequest,
    session: SessionDep,
    request: Request,
    response: Response,
    user_agent: Annotated[str | None, Header()] = None,
    mos_refresh_token: Annotated[str | None, Cookie()] = None,
) -> TokenResponse:
    raw = data.refresh_token or mos_refresh_token
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No refresh token.")
    try:
        tokens = service.refresh(
            session, raw, user_agent=user_agent, ip_address=_client_ip(request)
        )
    except service.AccountSuspendedError as exc:
        _clear_cookies(response)
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except service.AuthError as exc:
        _clear_cookies(response)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    _set_cookies(response, tokens)
    return _token_response(tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    data: RefreshRequest,
    session: SessionDep,
    response: Response,
    mos_refresh_token: Annotated[str | None, Cookie()] = None,
) -> None:
    """Always 204, token or not. Signing out is not a place to tell someone
    whether the thing they are holding was real."""
    raw = data.refresh_token or mos_refresh_token
    if raw:
        service.revoke(session, raw)
    _clear_cookies(response)


@router.get("/me", response_model=UserRead)
def me(user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(user)


@router.get("/sessions", response_model=list[SessionRead])
def list_sessions(user: CurrentUserDep, session: SessionDep) -> list[SessionRead]:
    """Where this account is currently signed in."""
    rows = session.exec(
        select(UserSession)
        .where(
            col(UserSession.user_id) == user.id,
            col(UserSession.revoked_at).is_(None),
        )
        .order_by(col(UserSession.created_at).desc())
    )
    return [SessionRead.model_validate(row) for row in rows]


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_everywhere(user: CurrentUserDep, session: SessionDep, response: Response) -> None:
    service.revoke_all(session, user.id)
    _clear_cookies(response)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    data: ChangePasswordRequest,
    user: CurrentUserDep,
    session: SessionDep,
    response: Response,
) -> None:
    """Every other session dies with the old password - see
    app.auth.service.change_password. This one too: the client is expected to
    sign in again, which is the only way it can be sure it holds a token
    minted after the change."""
    try:
        service.change_password(session, user, current=data.current_password, new=data.password)
    except service.AuthError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    _clear_cookies(response)
