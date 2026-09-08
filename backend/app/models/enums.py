from enum import StrEnum


class ExecutionStatus(StrEnum):
    """Shared status lifecycle for CampaignExecution and AgentExecution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CampaignStatus(StrEnum):
    """Lifecycle of the Campaign itself, independent of any single run."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class AssetType(StrEnum):
    """What a run produces. Only marketing deliverables belong here."""

    EMAIL = "email"
    SOCIAL_POST = "social_post"
    AD = "ad"
    BLOG = "blog"
    LANDING_PAGE = "landing_page"


class LogLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class UserRole(StrEnum):
    """What a platform account may do inside its own workspace.

    Deliberately short: the back-office has its own role ladder on AdminUser,
    and mixing the two is how a customer account ends up one flag away from
    reading everybody's campaigns.
    """

    OWNER = "owner"
    MEMBER = "member"


class UserStatus(StrEnum):
    """Whether an account may sign in at all.

    PENDING exists for the invite/verify flow; it authenticates like ACTIVE
    today and is here so turning verification on later is a policy change
    rather than a migration.
    """

    ACTIVE = "active"
    PENDING = "pending"
    SUSPENDED = "suspended"


class UserPlan(StrEnum):
    """Which tier an account is on. Prices live in the back-office, not here -
    a plan is an entitlement key, and putting a number on it in the product
    database means every price change is a migration."""

    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"


class AdminRole(StrEnum):
    """Back-office privilege ladder. Ordered: see app.auth.admin.ROLE_LEVELS."""

    SUPPORT = "support"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"
