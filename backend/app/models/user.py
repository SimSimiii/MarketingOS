from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from app.models.enums import UserPlan, UserRole, UserStatus


class User(SQLModel, table=True):
    """One account that can sign in, and the tenant everything it makes belongs to.

    Brands and campaigns carry `owner_id` pointing here; every other table
    hangs off one of those two, so scoping the two roots is what keeps two
    customers' work apart. See app.auth.scope.

    The password never reaches this row: `password_hash` is bcrypt over an
    HMAC of the password with a server-side pepper (app.auth.passwords), so a
    stolen database without the pepper is not a password list.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    #: Stored lower-cased. Lookups are done on the normalised form rather than
    #: with a case-insensitive comparison, because the second kind of query
    #: cannot use the unique index and this is the one query every request makes.
    email: str = Field(unique=True, index=True)
    password_hash: str
    full_name: str | None = None
    company_name: str | None = None

    role: UserRole = Field(default=UserRole.OWNER)
    status: UserStatus = Field(default=UserStatus.ACTIVE, index=True)
    plan: UserPlan = Field(default=UserPlan.FREE, index=True)

    #: Why an admin suspended this account, shown back to the user at login so
    #: a locked-out customer knows whether to write in or pay an invoice.
    suspended_reason: str | None = None

    #: Runs allowed in the current period and runs already spent. The pricing
    #: work has not landed - these are counters the back-office can already
    #: read and grant against, so turning metering on later does not need a
    #: migration on a table that by then has customers in it. 0 = unlimited.
    monthly_run_quota: int = Field(default=0)
    runs_used: int = Field(default=0)
    #: When `runs_used` was last rolled back to zero.
    quota_reset_at: datetime | None = None

    #: Set once the address is confirmed. Nothing enforces it yet; see UserStatus.
    email_verified_at: datetime | None = None
    last_login_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_active(self) -> bool:
        return self.status != UserStatus.SUSPENDED


class UserSession(SQLModel, table=True):
    """One refresh token, so a session can be ended from the server.

    Access tokens are stateless and short-lived - checking them against the
    database on every request would put a query in front of every page for a
    revocation that has never happened. The refresh token is the opposite: it
    is used rarely and must be revocable, which is the whole reason "sign out
    everywhere" and the back-office's force-logout can exist at all.

    Only the hash is stored. A leaked backup is then a list of useless digests
    rather than a set of live sessions.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    token_hash: str = Field(unique=True, index=True)
    expires_at: datetime
    revoked_at: datetime | None = None
    #: Kept for the "where you are signed in" list and for an admin reading an
    #: incident, not for authorisation - both are client-supplied.
    user_agent: str | None = None
    ip_address: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_used_at: datetime | None = None
