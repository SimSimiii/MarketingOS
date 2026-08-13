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
