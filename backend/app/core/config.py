from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

#: backend/prompts - every prompt template lives here, loaded via
#: app.runtime.prompt_engine.PromptEngine. Never hardcoded in Python.
PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


class Settings(BaseSettings):
    """Central application configuration, sourced from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"

    database_url: str = "sqlite:///./marketingos.db"

    ai_provider: Literal["claude", "openai", "gemini", "local"] = "claude"
    anthropic_model: str = "claude-sonnet-4-6"

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Settings are cached for the lifetime of the process (single source of truth)."""
    return Settings()
