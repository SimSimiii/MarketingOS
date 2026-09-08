from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

#: backend/prompts - every prompt template lives here, loaded via
#: app.runtime.prompt_engine.PromptEngine. Never hardcoded in Python.
PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

#: Sentinels, not secrets. Development and the test suite need *some*
#: signing material and nobody should have to invent it to run the app;
#: `get_settings` refuses to boot a production process that still has these.
DEV_JWT_SECRET = "dev-only-jwt-secret-change-me-before-you-deploy-anything"
DEV_PASSWORD_PEPPER = "dev-only-password-pepper-change-me-before-you-deploy"


class Settings(BaseSettings):
    """Central application configuration, sourced from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"

    database_url: str = "sqlite:///./marketingos.db"

    #: The vendor a call falls back to when its model does not name one. Both
    #: backends are always built - see app.ai.factory - so this is a default,
    #: not a switch that turns the other vendor off.
    ai_provider: Literal["claude", "openai", "gemini", "local"] = "claude"
    anthropic_model: str = "claude-sonnet-4-6"
    #: Mirrors app.ai.models.OpenAIModel.SOL - Codex's own default for a
    #: ChatGPT-authenticated session. Spelled out rather than imported to keep
    #: settings free of application imports.
    openai_model: str = "gpt-5.6-sol"

    cors_origins: str = "http://localhost:3000"

    # ── Authentication ───────────────────────────────────────────────────────
    #: Signs access and refresh tokens. The default is a marker, not a secret:
    #: `get_settings` refuses to start a production process still carrying it.
    jwt_secret: str = DEV_JWT_SECRET
    #: Folded into every password before bcrypt (app.auth.passwords). Kept out
    #: of the database on purpose - the point is that a stolen dump alone is
    #: not enough to mount an offline attack.
    password_pepper: str = DEV_PASSWORD_PEPPER
    #: Short by design. A revoked account keeps working for at most this long,
    #: because access tokens are verified by signature and never looked up.
    access_token_ttl_minutes: int = 60
    #: Long, and revocable: refresh tokens are rows (app.models.user.UserSession),
    #: so signing out - or an admin forcing it - takes effect immediately.
    refresh_token_ttl_days: int = 30

    #: Whether the API demands a token. False leaves the product exactly as it
    #: was before accounts existed: one workspace, no login, every row visible.
    #: That is the right default for a laptop and the wrong one for a server,
    #: so production overrides it below and cannot turn it back off.
    auth_required: bool = False
    #: Whether strangers may create their own account. Off by default: the
    #: first deployments are invited testers, and an open signup form on a
    #: product that spends model quota per run is a bill, not a funnel.
    allow_public_signup: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Settings are cached for the lifetime of the process (single source of truth)."""
    settings = Settings()
    if settings.is_production:
        # Two things a production process must never be: reachable without a
        # token, and signing tokens with a secret that is printed in this file.
        # Both are startup failures rather than warnings, because the failure
        # they prevent is silent and the log line would be read afterwards.
        settings.auth_required = True
        insecure = [
            name
            for name, value, default in (
                ("JWT_SECRET", settings.jwt_secret, DEV_JWT_SECRET),
                ("PASSWORD_PEPPER", settings.password_pepper, DEV_PASSWORD_PEPPER),
            )
            if value == default
        ]
        if insecure:
            raise RuntimeError(
                "Refusing to start in production with development secrets still set: "
                + ", ".join(insecure)
                + ". Generate one each with `python -c \"import secrets;"
                " print(secrets.token_hex(32))\"`."
            )
    return settings
