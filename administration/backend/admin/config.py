"""Settings for the back-office, and only for the back-office.

Everything about the *product* - the database URL, the model catalogue - is
read by the reused `app` package through its own `app.core.config.Settings`,
so the admin Lambda's environment carries both. What lives here is the handful
of things that exist because this is a separate front door.

The signing secret is the important one. It must differ from the platform's
`JWT_SECRET`: two systems that trust each other's tokens are one system, and
the whole point of a separate operator table is that a stolen customer token
buys nothing here.
"""

from __future__ import annotations

import json
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_ADMIN_JWT_SECRET = "dev-only-admin-jwt-secret-change-me-before-you-deploy"
DEV_ADMIN_PEPPER = "dev-only-admin-pepper-change-me-before-you-deploy-please"


class AdminSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    environment: str = "dev"
    log_level: str = "INFO"

    admin_jwt_secret: str = DEV_ADMIN_JWT_SECRET
    admin_pwd_pepper: str = DEV_ADMIN_PEPPER
    #: Shorter than the platform's refresh window on purpose. An operator
    #: session can read and change every customer account, so it is worth
    #: making someone sign in again once a day.
    admin_jwt_ttl_hours: int = 12

    #: Kept as raw strings rather than list/dict types. Pydantic tries to
    #: JSON-decode a complex-typed env var at construction and crashes on a
    #: plain comma-separated value, which is what a CloudFormation parameter
    #: naturally produces. Parsed lazily below instead.
    admin_cors_origins: str = "http://localhost:3001"
    #: Monthly price per paid plan, for the revenue estimate on the overview.
    #: Here rather than in the product database on purpose: a price is a
    #: business fact that changes, and a column for it would make every change
    #: a migration on a table that has customers in it.
    admin_plan_prices: str = '{"free": 0, "pro": 49, "business": 149}'

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in ("prod", "production")

    @property
    def cors_origins_list(self) -> list[str]:
        raw = self.admin_cors_origins.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed]
        except (ValueError, TypeError):
            pass
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def plan_prices(self) -> dict[str, float]:
        try:
            return {key: float(value) for key, value in json.loads(self.admin_plan_prices).items()}
        except (ValueError, TypeError, AttributeError):
            return {}


@lru_cache(maxsize=1)
def get_admin_settings() -> AdminSettings:
    settings = AdminSettings()
    if settings.is_production:
        insecure = [
            name
            for name, value, default in (
                ("ADMIN_JWT_SECRET", settings.admin_jwt_secret, DEV_ADMIN_JWT_SECRET),
                ("ADMIN_PWD_PEPPER", settings.admin_pwd_pepper, DEV_ADMIN_PEPPER),
            )
            if value == default
        ]
        if insecure:
            raise RuntimeError(
                "Refusing to start the back-office in production with development secrets "
                "still set: " + ", ".join(insecure)
            )
    return settings
