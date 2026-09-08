"""Customer accounts: read them, and change the few things support changes.

Reads are open to any operator. Everything that changes an account needs
`admin` or higher, and deleting one needs `superadmin` - see
app.models.enums.AdminRole and ..auth.require_role.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from app.models.admin import AdminUser
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.enums import AdminRole
from fastapi import APIRouter, Depends, Query, Request
from sqlmodel import Session, col, select

from .. import service
from ..auth import CurrentAdminDep, require_role
from ..db import get_session
from ..schemas import (
    PlanChangeRequest,
    QuotaRequest,
    SuspendRequest,
    UserDetail,
    UserListResponse,
)

router = APIRouter(prefix="/api/users", tags=["users"])

SessionDep = Annotated[Session, Depends(get_session)]
AdminWriterDep = Annotated[AdminUser, Depends(require_role(AdminRole.ADMIN))]
SuperAdminDep = Annotated[AdminUser, Depends(require_role(AdminRole.SUPERADMIN))]


@router.get("", response_model=UserListResponse)
def list_users(
    session: SessionDep,
    _: CurrentAdminDep,
    search: str | None = Query(default=None),
    plan: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> UserListResponse:
    items, total = service.list_users(
        session,
        search=search,
        plan=plan,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    return UserListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{user_id}", response_model=UserDetail)
def get_user(user_id: UUID, session: SessionDep, _: CurrentAdminDep) -> UserDetail:
    return service.user_detail(session, service.get_user_or_404(session, user_id))


@router.get("/{user_id}/workspace")
def get_user_workspace(user_id: UUID, session: SessionDep, _: CurrentAdminDep) -> dict:
    """The names of what this account has built - not its contents.

    Support needs to recognise an account ("the one with three brands, one
    called Acme"), and does not need to read the customer's copy. Names and
    counts answer the first question without answering the second.
    """
    user = service.get_user_or_404(session, user_id)
    brands = list(session.exec(select(Brand).where(col(Brand.owner_id) == user.id)))
    campaigns = list(session.exec(select(Campaign).where(col(Campaign.owner_id) == user.id)))
    return {
        "brands": [
            {"id": str(brand.id), "name": brand.name, "created_at": brand.created_at}
            for brand in brands
        ],
        "campaigns": [
            {
                "id": str(campaign.id),
                "name": campaign.name,
                "status": str(campaign.status),
                "created_at": campaign.created_at,
            }
            for campaign in campaigns
        ],
    }


@router.patch("/{user_id}/plan", response_model=UserDetail)
def change_plan(
    user_id: UUID,
    data: PlanChangeRequest,
    request: Request,
    session: SessionDep,
    admin: AdminWriterDep,
) -> UserDetail:
    user = service.get_user_or_404(session, user_id)
    return service.change_plan(
        session, admin, user, data.plan, data.monthly_run_quota, data.reason,
        service.client_ip(request),
    )


@router.patch("/{user_id}/quota", response_model=UserDetail)
def set_quota(
    user_id: UUID,
    data: QuotaRequest,
    request: Request,
    session: SessionDep,
    admin: AdminWriterDep,
) -> UserDetail:
    user = service.get_user_or_404(session, user_id)
    return service.set_quota(
        session, admin, user, data.monthly_run_quota, data.runs_used, data.reason,
        service.client_ip(request),
    )


@router.post("/{user_id}/suspend", response_model=UserDetail)
def suspend(
    user_id: UUID,
    data: SuspendRequest,
    request: Request,
    session: SessionDep,
    admin: AdminWriterDep,
) -> UserDetail:
    user = service.get_user_or_404(session, user_id)
    return service.set_suspended(
        session, admin, user, True, data.reason, service.client_ip(request)
    )


@router.post("/{user_id}/unsuspend", response_model=UserDetail)
def unsuspend(
    user_id: UUID, request: Request, session: SessionDep, admin: AdminWriterDep
) -> UserDetail:
    user = service.get_user_or_404(session, user_id)
    return service.set_suspended(session, admin, user, False, None, service.client_ip(request))


@router.post("/{user_id}/sign-out")
def sign_out(
    user_id: UUID, request: Request, session: SessionDep, admin: AdminWriterDep
) -> dict[str, int]:
    user = service.get_user_or_404(session, user_id)
    return service.sign_out_everywhere(session, admin, user, service.client_ip(request))


@router.delete("/{user_id}")
def delete_user(
    user_id: UUID, request: Request, session: SessionDep, admin: SuperAdminDep
) -> dict[str, str]:
    user = service.get_user_or_404(session, user_id)
    return service.delete_user(session, admin, user, service.client_ip(request))
