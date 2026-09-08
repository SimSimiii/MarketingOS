"""Request and response shapes for the back-office API."""

from __future__ import annotations

from uuid import UUID

from app.models.enums import AdminRole, UserPlan
from app.schemas.types import UtcDatetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

MIN_ADMIN_PASSWORD_LENGTH = 12


class _PasswordRules:
    @field_validator("password", check_fields=False)
    @classmethod
    def _long_enough(cls, value: str) -> str:
        if len(value) < MIN_ADMIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Password must be at least {MIN_ADMIN_PASSWORD_LENGTH} characters."
            )
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None
    role: AdminRole
    is_active: bool
    last_login_at: UtcDatetime | None
    created_at: UtcDatetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    admin: AdminRead


class AdminCreateRequest(_PasswordRules, BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = Field(default=None, max_length=120)
    role: AdminRole = AdminRole.SUPPORT


class AdminUpdateRequest(BaseModel):
    full_name: str | None = None
    role: AdminRole | None = None
    is_active: bool | None = None


class AdminPasswordRequest(_PasswordRules, BaseModel):
    password: str


# ── Customers ────────────────────────────────────────────────────────────────


class UserSummary(BaseModel):
    """One row of the users table. Counts included, because a list of accounts
    with no sign of what is in them is a list of email addresses."""

    id: UUID
    email: str
    full_name: str | None
    company_name: str | None
    plan: UserPlan
    status: str
    monthly_run_quota: int
    runs_used: int
    brands: int
    campaigns: int
    runs: int
    created_at: UtcDatetime
    last_login_at: UtcDatetime | None


class UserListResponse(BaseModel):
    items: list[UserSummary]
    total: int
    limit: int
    offset: int


class UserDetail(UserSummary):
    suspended_reason: str | None
    active_sessions: int
    #: Tokens and estimated spend across every run this account has made.
    #: The number that decides whether a plan is priced right.
    total_input_tokens: int
    total_output_tokens: int
    estimated_cost_usd: float
    last_run_at: UtcDatetime | None


class PlanChangeRequest(BaseModel):
    plan: UserPlan
    #: Runs per period the new plan grants. Left out means "leave the quota
    #: alone", which is what makes moving somebody to a plan without resetting
    #: a manual grant possible.
    monthly_run_quota: int | None = Field(default=None, ge=0)
    reason: str | None = Field(default=None, max_length=500)


class QuotaRequest(BaseModel):
    """Set the quota, or hand back some of the period.

    `monthly_run_quota` sets the ceiling; `runs_used` sets the counter, which
    is how support gives a tester their runs back after a failed batch.
    """

    monthly_run_quota: int | None = Field(default=None, ge=0)
    runs_used: int | None = Field(default=None, ge=0)
    reason: str | None = Field(default=None, max_length=500)


class SuspendRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class AuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    admin_email: str | None
    action: str
    target_type: str | None
    target_id: str | None
    detail: dict | None
    ip_address: str | None
    created_at: UtcDatetime


class OverviewResponse(BaseModel):
    """What the back-office shows first."""

    users_total: int
    users_active: int
    users_suspended: int
    users_by_plan: dict[str, int]
    signups_last_7_days: int
    signups_last_30_days: int
    brands_total: int
    campaigns_total: int
    runs_total: int
    runs_last_7_days: int
    runs_failed_last_7_days: int
    tokens_total: int
    model_spend_usd: float
    #: Monthly recurring revenue implied by today's plan mix and the price map
    #: in ADMIN_PLAN_PRICES. An estimate, and labelled one in the UI: nothing
    #: here has been through a payment processor yet.
    estimated_mrr_usd: float


class TimeseriesPoint(BaseModel):
    day: str
    value: float


class TimeseriesResponse(BaseModel):
    metric: str
    days: int
    series: list[TimeseriesPoint]
