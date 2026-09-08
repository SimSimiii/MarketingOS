"""What the back-office knows and what it may change.

Two rules run through everything here:

- **The counts come from grouped queries, not from loops.** A back-office that
  issues one query per row is a back-office that gets slower exactly as the
  business it is watching gets bigger.
- **Every change writes an audit row on the same session as the change.** They
  commit together or not at all - an audit log that can silently miss the one
  entry somebody cared about is worse than no audit log, because it is
  trusted.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.models.admin import AdminAuditLog, AdminUser
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.campaign_execution import CampaignExecution
from app.models.enums import ExecutionStatus, UserPlan, UserStatus
from app.models.user import User, UserSession
from app.models.user_settings import UserSettings
from fastapi import HTTPException, Request, status
from sqlalchemy import delete, func
from sqlmodel import Session, col, select

from .config import get_admin_settings
from .schemas import (
    OverviewResponse,
    TimeseriesPoint,
    UserDetail,
    UserSummary,
)


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return request.client.host if request.client else None


def log_action(
    session: Session,
    admin: AdminUser | None,
    action: str,
    *,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: dict | None = None,
    ip: str | None = None,
) -> None:
    """Append one audit row. Does not commit - the caller does, once, with the
    change the row describes."""
    session.add(
        AdminAuditLog(
            admin_id=admin.id if admin else None,
            admin_email=admin.email if admin else None,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            detail=detail,
            ip_address=ip,
        )
    )


def get_user_or_404(session: Session, user_id: UUID) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such account.")
    return user


# ── Counting ─────────────────────────────────────────────────────────────────


def _counts_by_owner(session: Session, model: type) -> dict[UUID, int]:
    """How many rows of an owned table each account has, in one query."""
    statement = (
        select(model.owner_id, func.count())  # type: ignore[attr-defined]
        .where(col(model.owner_id).is_not(None))  # type: ignore[attr-defined]
        .group_by(col(model.owner_id))  # type: ignore[attr-defined]
    )
    return {owner_id: total for owner_id, total in session.exec(statement) if owner_id}


def _runs_by_owner(session: Session) -> dict[UUID, int]:
    """Runs per account. Two hops - a run belongs to a campaign, and the
    campaign is what carries the owner."""
    statement = (
        select(Campaign.owner_id, func.count(col(CampaignExecution.id)))
        .join(CampaignExecution, col(CampaignExecution.campaign_id) == col(Campaign.id))
        .where(col(Campaign.owner_id).is_not(None))
        .group_by(col(Campaign.owner_id))
    )
    return {owner_id: total for owner_id, total in session.exec(statement) if owner_id}


def _as_datetime(value: object) -> datetime | None:
    """SQLite hands `max()` over a DATETIME column back as a string."""
    if value is None or isinstance(value, datetime):
        return value  # type: ignore[return-value]
    return datetime.fromisoformat(str(value))


def list_users(
    session: Session,
    *,
    search: str | None = None,
    plan: str | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[UserSummary], int]:
    statement = select(User)
    if search:
        needle = f"%{search.strip().lower()}%"
        statement = statement.where(
            func.lower(col(User.email)).like(needle)
            | func.lower(func.coalesce(col(User.full_name), "")).like(needle)
            | func.lower(func.coalesce(col(User.company_name), "")).like(needle)
        )
    if plan:
        statement = statement.where(col(User.plan) == UserPlan(plan))
    if status_filter:
        statement = statement.where(col(User.status) == UserStatus(status_filter))

    total = session.exec(
        select(func.count()).select_from(statement.subquery())
    ).one()
    rows = list(
        session.exec(
            statement.order_by(col(User.created_at).desc()).offset(offset).limit(limit)
        )
    )

    brands = _counts_by_owner(session, Brand)
    campaigns = _counts_by_owner(session, Campaign)
    runs = _runs_by_owner(session)
    return [
        UserSummary(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            company_name=user.company_name,
            plan=user.plan,
            status=str(user.status),
            monthly_run_quota=user.monthly_run_quota,
            runs_used=user.runs_used,
            brands=brands.get(user.id, 0),
            campaigns=campaigns.get(user.id, 0),
            runs=runs.get(user.id, 0),
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
        for user in rows
    ], total


def user_detail(session: Session, user: User) -> UserDetail:
    brands = session.exec(
        select(func.count()).select_from(Brand).where(col(Brand.owner_id) == user.id)
    ).one()
    campaigns = session.exec(
        select(func.count()).select_from(Campaign).where(col(Campaign.owner_id) == user.id)
    ).one()
    sessions_live = session.exec(
        select(func.count())
        .select_from(UserSession)
        .where(col(UserSession.user_id) == user.id, col(UserSession.revoked_at).is_(None))
    ).one()

    spend = session.exec(
        select(
            func.count(col(CampaignExecution.id)),
            func.coalesce(func.sum(col(CampaignExecution.total_input_tokens)), 0),
            func.coalesce(func.sum(col(CampaignExecution.total_output_tokens)), 0),
            func.coalesce(func.sum(col(CampaignExecution.estimated_cost_usd)), 0.0),
            func.max(col(CampaignExecution.created_at)),
        )
        .select_from(CampaignExecution)
        .join(Campaign, col(CampaignExecution.campaign_id) == col(Campaign.id))
        .where(col(Campaign.owner_id) == user.id)
    ).one()
    runs, input_tokens, output_tokens, cost, last_run = spend

    return UserDetail(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        company_name=user.company_name,
        plan=user.plan,
        status=str(user.status),
        monthly_run_quota=user.monthly_run_quota,
        runs_used=user.runs_used,
        brands=brands,
        campaigns=campaigns,
        runs=runs,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        suspended_reason=user.suspended_reason,
        active_sessions=sessions_live,
        total_input_tokens=int(input_tokens or 0),
        total_output_tokens=int(output_tokens or 0),
        estimated_cost_usd=round(float(cost or 0.0), 4),
        last_run_at=_as_datetime(last_run),
    )


# ── Changing ─────────────────────────────────────────────────────────────────


def change_plan(
    session: Session,
    admin: AdminUser,
    user: User,
    plan: UserPlan,
    quota: int | None,
    reason: str | None,
    ip: str | None,
) -> UserDetail:
    before = {"plan": str(user.plan), "monthly_run_quota": user.monthly_run_quota}
    user.plan = plan
    if quota is not None:
        user.monthly_run_quota = quota
    user.updated_at = datetime.now(UTC)
    session.add(user)
    log_action(
        session,
        admin,
        "user.plan_change",
        target_type="user",
        target_id=user.id,
        detail={
            "before": before,
            "after": {"plan": str(plan), "monthly_run_quota": user.monthly_run_quota},
            "reason": reason,
        },
        ip=ip,
    )
    session.commit()
    session.refresh(user)
    return user_detail(session, user)


def set_quota(
    session: Session,
    admin: AdminUser,
    user: User,
    quota: int | None,
    runs_used: int | None,
    reason: str | None,
    ip: str | None,
) -> UserDetail:
    before = {"monthly_run_quota": user.monthly_run_quota, "runs_used": user.runs_used}
    if quota is not None:
        user.monthly_run_quota = quota
    if runs_used is not None:
        user.runs_used = runs_used
        user.quota_reset_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    session.add(user)
    log_action(
        session,
        admin,
        "user.quota_change",
        target_type="user",
        target_id=user.id,
        detail={
            "before": before,
            "after": {
                "monthly_run_quota": user.monthly_run_quota,
                "runs_used": user.runs_used,
            },
            "reason": reason,
        },
        ip=ip,
    )
    session.commit()
    session.refresh(user)
    return user_detail(session, user)


def set_suspended(
    session: Session,
    admin: AdminUser,
    user: User,
    suspended: bool,
    reason: str | None,
    ip: str | None,
) -> UserDetail:
    """Suspending also ends every live session.

    Without that, a suspension only stops the *next* sign-in: the account's
    refresh token would keep minting access tokens, and the access token it
    already holds keeps working until it expires. Revoking here is what makes
    "suspended" mean suspended now.
    """
    user.status = UserStatus.SUSPENDED if suspended else UserStatus.ACTIVE
    user.suspended_reason = reason if suspended else None
    user.updated_at = datetime.now(UTC)
    session.add(user)

    revoked = 0
    if suspended:
        now = datetime.now(UTC)
        for record in session.exec(
            select(UserSession).where(
                col(UserSession.user_id) == user.id, col(UserSession.revoked_at).is_(None)
            )
        ):
            record.revoked_at = now
            session.add(record)
            revoked += 1

    log_action(
        session,
        admin,
        "user.suspend" if suspended else "user.unsuspend",
        target_type="user",
        target_id=user.id,
        detail={"reason": reason, "sessions_revoked": revoked},
        ip=ip,
    )
    session.commit()
    session.refresh(user)
    return user_detail(session, user)


def sign_out_everywhere(
    session: Session, admin: AdminUser, user: User, ip: str | None
) -> dict[str, int]:
    now = datetime.now(UTC)
    revoked = 0
    for record in session.exec(
        select(UserSession).where(
            col(UserSession.user_id) == user.id, col(UserSession.revoked_at).is_(None)
        )
    ):
        record.revoked_at = now
        session.add(record)
        revoked += 1
    log_action(
        session,
        admin,
        "user.force_logout",
        target_type="user",
        target_id=user.id,
        detail={"sessions_revoked": revoked},
        ip=ip,
    )
    session.commit()
    return {"sessions_revoked": revoked}


def delete_user(session: Session, admin: AdminUser, user: User, ip: str | None) -> dict[str, str]:
    """Remove the account and unown its work.

    The brands and campaigns are *not* deleted. A support request to close an
    account is not a request to destroy the work in it, deleting it would
    cascade through knowledge, market and every run, and an unowned row is
    already invisible to everyone on a deployment that requires auth. If it
    really should go, it can be deleted from the product with the account
    still alive.
    """
    email = user.email
    for model in (Brand, Campaign):
        for row in session.exec(select(model).where(col(model.owner_id) == user.id)):
            row.owner_id = None
            session.add(row)
    session.exec(delete(UserSettings).where(col(UserSettings.user_id) == user.id))
    session.exec(delete(UserSession).where(col(UserSession.user_id) == user.id))

    log_action(
        session,
        admin,
        "user.delete",
        target_type="user",
        target_id=user.id,
        detail={"email": email},
        ip=ip,
    )
    session.delete(user)
    session.commit()
    return {"deleted": email}


# ── Overview ─────────────────────────────────────────────────────────────────


def _since(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


def overview(session: Session) -> OverviewResponse:
    users_total = session.exec(select(func.count()).select_from(User)).one()
    by_plan = {
        str(plan): total
        for plan, total in session.exec(
            select(User.plan, func.count()).group_by(col(User.plan))
        )
    }
    by_status = {
        str(state): total
        for state, total in session.exec(
            select(User.status, func.count()).group_by(col(User.status))
        )
    }

    runs_total = session.exec(select(func.count()).select_from(CampaignExecution)).one()
    recent_runs = session.exec(
        select(func.count())
        .select_from(CampaignExecution)
        .where(col(CampaignExecution.created_at) >= _since(7))
    ).one()
    failed_runs = session.exec(
        select(func.count())
        .select_from(CampaignExecution)
        .where(
            col(CampaignExecution.created_at) >= _since(7),
            col(CampaignExecution.status) == ExecutionStatus.FAILED,
        )
    ).one()
    tokens, spend = session.exec(
        select(
            func.coalesce(
                func.sum(
                    col(CampaignExecution.total_input_tokens)
                    + col(CampaignExecution.total_output_tokens)
                ),
                0,
            ),
            func.coalesce(func.sum(col(CampaignExecution.estimated_cost_usd)), 0.0),
        )
    ).one()

    prices = get_admin_settings().plan_prices
    mrr = sum(prices.get(plan, 0.0) * count for plan, count in by_plan.items())

    return OverviewResponse(
        users_total=users_total,
        users_active=by_status.get(str(UserStatus.ACTIVE), 0),
        users_suspended=by_status.get(str(UserStatus.SUSPENDED), 0),
        users_by_plan=by_plan,
        signups_last_7_days=session.exec(
            select(func.count()).select_from(User).where(col(User.created_at) >= _since(7))
        ).one(),
        signups_last_30_days=session.exec(
            select(func.count()).select_from(User).where(col(User.created_at) >= _since(30))
        ).one(),
        brands_total=session.exec(select(func.count()).select_from(Brand)).one(),
        campaigns_total=session.exec(select(func.count()).select_from(Campaign)).one(),
        runs_total=runs_total,
        runs_last_7_days=recent_runs,
        runs_failed_last_7_days=failed_runs,
        tokens_total=int(tokens or 0),
        model_spend_usd=round(float(spend or 0.0), 2),
        estimated_mrr_usd=round(mrr, 2),
    )


#: metric name -> (model, timestamp column, value expression). `None` for the
#: value means "count the rows".
_TIMESERIES = {
    "signups": (User, User.created_at, None),
    "runs": (CampaignExecution, CampaignExecution.created_at, None),
    "campaigns": (Campaign, Campaign.created_at, None),
}


def timeseries(session: Session, metric: str, days: int) -> list[TimeseriesPoint]:
    """One value per day, zero-filled.

    Zero-filling in Python rather than in SQL because neither SQLite nor
    Postgres generates a date series the same way, and a chart with holes in
    it reads as "nothing happened on the days that are missing" only if the
    days are there.
    """
    if metric not in _TIMESERIES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unknown metric '{metric}'. Try one of: {', '.join(_TIMESERIES)}.",
        )
    _model, timestamp, _value = _TIMESERIES[metric]
    start = _since(days)
    rows = session.exec(
        select(timestamp).where(col(timestamp) >= start)  # type: ignore[arg-type]
    )

    tally: dict[str, int] = defaultdict(int)
    for value in rows:
        moment = _as_datetime(value)
        if moment is not None:
            tally[moment.date().isoformat()] += 1

    today = datetime.now(UTC).date()
    return [
        TimeseriesPoint(
            day=(today - timedelta(days=offset)).isoformat(),
            value=tally.get((today - timedelta(days=offset)).isoformat(), 0),
        )
        for offset in reversed(range(days))
    ]
