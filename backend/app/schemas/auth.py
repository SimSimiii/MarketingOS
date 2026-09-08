from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import UserPlan, UserRole, UserStatus
from app.schemas.types import UtcDatetime

#: Short enough that nobody is locked out of their own product, long enough
#: that the bcrypt cost is not the only thing standing between an attacker and
#: the account. Length is the only rule: composition rules push people toward
#: `Password1!` and no further.
MIN_PASSWORD_LENGTH = 10


class _PasswordRules:
    @field_validator("password", check_fields=False)
    @classmethod
    def _long_enough(cls, value: str) -> str:
        if len(value) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        return value


class RegisterRequest(_PasswordRules, BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = Field(default=None, max_length=120)
    company_name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """The refresh token, when the client cannot send it as a cookie."""

    refresh_token: str | None = None


class ChangePasswordRequest(_PasswordRules, BaseModel):
    current_password: str
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None
    company_name: str | None
    role: UserRole
    status: UserStatus
    plan: UserPlan
    monthly_run_quota: int
    runs_used: int
    created_at: UtcDatetime
    last_login_at: UtcDatetime | None


class TokenResponse(BaseModel):
    """A signed-in session.

    `expires_in` is seconds, and it is here rather than left in the JWT so a
    client schedules its refresh from a value the server stated.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_agent: str | None
    ip_address: str | None
    created_at: UtcDatetime
    last_used_at: UtcDatetime | None
    expires_at: UtcDatetime


class AuthConfigRead(BaseModel):
    """What the sign-in page needs to know before anyone types anything:
    whether to show a "create account" link, and whether this deployment has
    login at all."""

    auth_required: bool
    allow_public_signup: bool
