"""Operators, and the record of what they did.

Creating and changing operators is superadmin-only. The audit log is readable
by anyone who can sign in here, deliberately: a trail that only the people
with the most power can read is a trail that mostly protects them.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from app.models.admin import AdminAuditLog, AdminUser
from app.models.enums import AdminRole
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel import Session, col, func, select

from .. import service
from ..auth import CurrentAdminDep, hash_password, require_role
from ..db import get_session
from ..schemas import (
    AdminCreateRequest,
    AdminPasswordRequest,
    AdminRead,
    AdminUpdateRequest,
    AuditRead,
)

router = APIRouter(prefix="/api/admins", tags=["admins"])
audit_router = APIRouter(prefix="/api/audit", tags=["audit"])

SessionDep = Annotated[Session, Depends(get_session)]
SuperAdminDep = Annotated[AdminUser, Depends(require_role(AdminRole.SUPERADMIN))]


def _get_or_404(session: Session, admin_id: UUID) -> AdminUser:
    admin = session.get(AdminUser, admin_id)
    if admin is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such operator.")
    return admin


@router.get("", response_model=list[AdminRead])
def list_admins(session: SessionDep, _: CurrentAdminDep) -> list[AdminRead]:
    rows = session.exec(select(AdminUser).order_by(col(AdminUser.created_at)))
    return [AdminRead.model_validate(row) for row in rows]


@router.post("", response_model=AdminRead, status_code=status.HTTP_201_CREATED)
def create_admin(
    data: AdminCreateRequest, request: Request, session: SessionDep, admin: SuperAdminDep
) -> AdminRead:
    email = data.email.lower()
    existing = session.exec(
        select(AdminUser).where(func.lower(col(AdminUser.email)) == email)
    ).first()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "That address is already an operator.")

    created = AdminUser(
        email=email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
    )
    session.add(created)
    service.log_action(
        session,
        admin,
        "admin.create",
        target_type="admin",
        target_id=created.id,
        detail={"email": email, "role": str(data.role)},
        ip=service.client_ip(request),
    )
    session.commit()
    session.refresh(created)
    return AdminRead.model_validate(created)


@router.patch("/{admin_id}", response_model=AdminRead)
def update_admin(
    admin_id: UUID,
    data: AdminUpdateRequest,
    request: Request,
    session: SessionDep,
    admin: SuperAdminDep,
) -> AdminRead:
    target = _get_or_404(session, admin_id)
    if target.id == admin.id and data.is_active is False:
        # Not paternalism: the last superadmin locking themselves out means the
        # only way back in is the bootstrap script and shell access to the
        # database. Cheap to prevent, expensive to recover from.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate yourself.")

    before = {"role": str(target.role), "is_active": target.is_active}
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(target, field, value)
    target.updated_at = datetime.now(UTC)
    session.add(target)
    service.log_action(
        session,
        admin,
        "admin.update",
        target_type="admin",
        target_id=target.id,
        detail={
            "before": before,
            "after": {"role": str(target.role), "is_active": target.is_active},
        },
        ip=service.client_ip(request),
    )
    session.commit()
    session.refresh(target)
    return AdminRead.model_validate(target)


@router.post("/{admin_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def reset_admin_password(
    admin_id: UUID,
    data: AdminPasswordRequest,
    request: Request,
    session: SessionDep,
    admin: SuperAdminDep,
) -> None:
    target = _get_or_404(session, admin_id)
    target.password_hash = hash_password(data.password)
    target.updated_at = datetime.now(UTC)
    session.add(target)
    service.log_action(
        session,
        admin,
        "admin.password_reset",
        target_type="admin",
        target_id=target.id,
        # The password is not in here and must never be. The fact of the reset
        # is the auditable event; the value is not.
        detail={"email": target.email},
        ip=service.client_ip(request),
    )
    session.commit()


@audit_router.get("", response_model=list[AuditRead])
def list_audit(
    session: SessionDep,
    _: CurrentAdminDep,
    action: str | None = Query(default=None),
    target_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[AuditRead]:
    statement = select(AdminAuditLog)
    if action:
        statement = statement.where(col(AdminAuditLog.action) == action)
    if target_id:
        statement = statement.where(col(AdminAuditLog.target_id) == target_id)
    rows = session.exec(
        statement.order_by(col(AdminAuditLog.created_at).desc()).offset(offset).limit(limit)
    )
    return [AuditRead.model_validate(row) for row in rows]
