from functools import lru_cache

from app.ai.base import AIProvider
from app.core.config import get_settings


@lru_cache
def get_ai_provider() -> AIProvider:
    """Resolve the configured AIProvider. Add new branches here as vendors are implemented."""
    settings = get_settings()

    if settings.ai_provider == "claude":
        from app.ai.claude_provider import ClaudeProvider

        return ClaudeProvider(default_model=settings.anthropic_model)

    raise NotImplementedError(
        f"AI provider '{settings.ai_provider}' is not implemented yet. "
        "Only 'claude' is available in this MVP."
    )
