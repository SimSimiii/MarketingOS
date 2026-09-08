"""Operator sign-in.

No refresh token and no cookie, unlike the product. An operator session is
short and deliberate: it is signed in from one browser for a shift, and making
it survive a closed laptop is a convenience that is not worth the second
credential to steal.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated

from app.models.admin import AdminUser
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session, col, func, select

from .. import service
from ..auth import CurrentAdminDep, create_admin_token, verify_password
from ..db import get_session
from ..schemas import AdminRead, LoginRequest, TokenResponse

logger = logging.getLogger("marketingos.admin.auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> TokenResponse:
    admin = session.exec(
        select(AdminUser).where(func.lower(col(AdminUser.email)) == data.email.lower())
    ).first()

    # One message for both halves. Telling an unknown address apart from a
    # wrong password turns this form into a list of who operates the platform.
    if admin is None or not verify_password(data.password, admin.password_hash):
        logger.warning(
            "admin_login_failed email=%s ip=%s", data.email, service.client_ip(request)
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password.")
    if not admin.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated.")

    admin.last_login_at = datetime.now(UTC)
    session.add(admin)
    service.log_action(session, admin, "auth.login", ip=service.client_ip(request))
    session.commit()
    session.refresh(admin)

    token, expires_in = create_admin_token(admin)
    return TokenResponse(
        access_token=token, expires_in=expires_in, admin=AdminRead.model_validate(admin)
    )


@router.get("/me", response_model=AdminRead)
def me(admin: CurrentAdminDep) -> AdminRead:
    return AdminRead.model_validate(admin)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    admin: CurrentAdminDep,
    session: Annotated[Session, Depends(get_session)],
) -> None:
    """The token is stateless, so signing out is the client dropping it. The
    row is written anyway - the audit trail is about who was here and when,
    and a session with a start and no end reads as one that never finished."""
    service.log_action(session, admin, "auth.logout", ip=service.client_ip(request))
    session.commit()
