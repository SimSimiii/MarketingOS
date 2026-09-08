from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.enums import AdminRole


class AdminUser(SQLModel, table=True):
    """A back-office operator. Not a `User`, and deliberately a separate table.

    There is no public signup for these: the first one is created by
    `scripts/bootstrap_admin.py`, the rest by a superadmin from the
    back-office. Keeping them out of `user` means a bug in the customer signup
    path cannot mint an operator, and the two token families are signed with
    different secrets (see app.auth.admin) so a stolen customer token can
    never be replayed against the admin API.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    full_name: str | None = None
    role: AdminRole = Field(default=AdminRole.SUPPORT)
    is_active: bool = Field(default=True)
    last_login_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AdminAuditLog(SQLModel, table=True):
    """Every state-changing thing an operator did, append-only.

    Written by app.auth.admin_audit on the same session as the change itself,
    so an action and its trail commit together or not at all - an audit log
    that can silently miss the one entry someone cared about is worse than
    none, because it is trusted.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    admin_id: UUID | None = Field(default=None, foreign_key="adminuser.id", index=True)
    #: Denormalised so a deleted operator's actions stay readable.
    admin_email: str | None = None
    #: Dotted, e.g. "user.suspend", "user.plan_change", "auth.login".
    action: str = Field(index=True)
    target_type: str | None = None
    target_id: str | None = None
    #: What changed, before and after. Free-form on purpose: the shape differs
    #: per action and pinning it down would mean a migration per new action.
    detail: dict | None = Field(default=None, sa_column=Column(JSON))
    ip_address: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
