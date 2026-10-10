from sqlmodel import Field, SQLModel


class AuthRateLimit(SQLModel, table=True):
    """Shared password-attempt counter, without storing the supplied email."""

    key: str = Field(primary_key=True, max_length=64)
    window_start: int = Field(index=True)
    attempts: int = Field(default=1)
