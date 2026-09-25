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


def anthropic_backend(default_model: str) -> AIProvider:
    """Just the Anthropic half, for the one caller that wants a single vendor.

    Image ingestion reads a picture with a named Claude model and has no use
    for the router. It still has to honour `ai_billing`, or a Lambda would
    reach for the CLI through the side door and fail with a missing binary
    rather than a clear error - so the choice stays here rather than being
    made a second time at the call site.
    """
    settings = get_settings()
    if settings.ai_billing == "api":
        from app.ai.anthropic_api_provider import AnthropicAPIProvider

        return AnthropicAPIProvider(default_model=default_model)
    from app.ai.claude_provider import ClaudeProvider

    return ClaudeProvider(default_model=default_model)


@lru_cache
def get_ai_provider() -> AIProvider:
    """The provider every model call in the system goes through.

    Constructing both backends costs nothing - neither touches its CLI nor
    opens a socket until a call is made - and it is what lets a campaign put
    the writer on GPT and the critic on Claude without any caller knowing there
    is more than one vendor. A missing binary, or a missing API key, surfaces
    at the call that needed it, naming what to fix, rather than at import time
    on a machine that was never going to use that vendor.

    Which *pair* of backends is built comes from `Settings.ai_billing`: the
    subscription CLIs, or the metered HTTP APIs. Never a mix of the two - a run
    that billed one vendor's plan and the other's card is a run whose cost
    nobody can state.
    """
    settings = get_settings()
    if (default_vendor := _DEFAULT_VENDORS.get(settings.ai_provider)) is None:
        raise NotImplementedError(
            f"AI provider '{settings.ai_provider}' is not implemented. "
            f"Supported: {', '.join(sorted(_DEFAULT_VENDORS))}."
        )

    from app.ai.routing_provider import RoutingProvider

    # Imported inside the branch, never both. The CLI backends pull
    # `claude_agent_sdk`, which bundles a ~210 MB binary and costs about a
    # second of import - dead weight on a host that will never spawn the CLI,
    # and enough on its own to push a Lambda bundle past the 250 MB limit.
    if settings.ai_billing == "api":
        from app.ai.anthropic_api_provider import AnthropicAPIProvider
        from app.ai.openai_api_provider import OpenAIAPIProvider

        backends = {
            ModelVendor.ANTHROPIC: AnthropicAPIProvider(
                default_model=settings.anthropic_model
            ),
            ModelVendor.OPENAI: OpenAIAPIProvider(default_model=settings.openai_model),
        }
    else:
        from app.ai.claude_provider import ClaudeProvider
        from app.ai.openai_provider import OpenAIProvider

        backends = {
            ModelVendor.ANTHROPIC: ClaudeProvider(default_model=settings.anthropic_model),
            ModelVendor.OPENAI: OpenAIProvider(default_model=settings.openai_model),
        }

    return RoutingProvider(backends=backends, default_vendor=default_vendor)
