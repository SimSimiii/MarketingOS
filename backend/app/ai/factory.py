from functools import lru_cache

from app.ai.base import AIProvider
from app.ai.models import ModelVendor
from app.core.config import get_settings

#: `ai_provider` names the vendor a call falls back to when its model does not
#: say - an operator-typed slug the catalog does not recognise, or a role with
#: no override on a tier map that has been pointed somewhere unusual. It is no
#: longer a choice of *the* provider: with per-agent model selection a single
#: run routinely spans both, so both are always built.
_DEFAULT_VENDORS: dict[str, ModelVendor] = {
    "claude": ModelVendor.ANTHROPIC,
    "openai": ModelVendor.OPENAI,
}


@lru_cache
def get_ai_provider() -> AIProvider:
    """The provider every model call in the system goes through.

    Constructing both backends costs nothing - neither touches its CLI until a
    call is made - and it is what lets a campaign put the writer on GPT and the
    critic on Claude without any caller knowing there is more than one vendor.
    A missing binary surfaces at the call that needed it, naming what to
    install, rather than at import time on a machine that was never going to
    use that vendor.
    """
    settings = get_settings()
    if (default_vendor := _DEFAULT_VENDORS.get(settings.ai_provider)) is None:
        raise NotImplementedError(
            f"AI provider '{settings.ai_provider}' is not implemented. "
            f"Supported: {', '.join(sorted(_DEFAULT_VENDORS))}."
        )

    from app.ai.claude_provider import ClaudeProvider
    from app.ai.openai_provider import OpenAIProvider
    from app.ai.routing_provider import RoutingProvider

    return RoutingProvider(
        backends={
            ModelVendor.ANTHROPIC: ClaudeProvider(default_model=settings.anthropic_model),
            ModelVendor.OPENAI: OpenAIProvider(default_model=settings.openai_model),
        },
        default_vendor=default_vendor,
    )
