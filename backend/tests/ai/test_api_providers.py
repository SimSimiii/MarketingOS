"""The metered HTTP providers, and the four things that silently cost money.

`test_claude_provider` and `test_openai_provider` guard the subscription side:
that no API credential survives into a CLI subprocess. These are the other
half, and the risks invert. Here the key is *meant* to be used, so the tests
worth writing are the ones about a call that fails, bills twice, or bills at
all when the operator thought it would not:

  1. `temperature` reaching a model that rejects it - a 400 on every call.
  2. Cached input counted twice, which inflates a run's budget arithmetic.
  3. A retryable failure classified as permanent, or the reverse.
  4. `ai_billing` choosing the wrong pair of backends, which is the one that
     charges a card when the operator expected their plan to pay.
"""

import pytest

from app.ai.anthropic_api_provider import AnthropicAPIProvider, resolve_model
from app.ai.anthropic_api_provider import _as_call_error as anthropic_error
from app.ai.anthropic_api_provider import _usage as anthropic_usage
from app.ai.base import AIMessage, AIRequest, ProviderCallError, ResearchTool
from app.ai.openai_api_provider import OpenAIAPIProvider
from app.ai.openai_api_provider import _as_call_error as openai_error
from app.ai.openai_api_provider import _usage as openai_usage


def _request(**kwargs) -> AIRequest:
    return AIRequest(
        system_prompt=kwargs.pop("system_prompt", "You are terse."),
        messages=[AIMessage(role="user", content=kwargs.pop("task", "Say OK"))],
        **kwargs,
    )


class _Usage:
    def __init__(self, **fields):
        for key, value in fields.items():
            setattr(self, key, value)


# ───────────────────────────────── model ids ─────────────────────────────────


def test_catalog_aliases_resolve_to_full_api_model_ids():
    """The catalog stores CLI aliases because the CLI resolves them itself.
    The HTTP API does not - it 404s on `sonnet`."""
    assert resolve_model("sonnet") == "claude-sonnet-5"
    assert resolve_model("haiku") == "claude-haiku-4-5"
    assert resolve_model("opus") == "claude-opus-5"
    assert resolve_model("fable5") == "claude-fable-5-1"


def test_a_full_model_id_passes_through_untouched():
    assert resolve_model("claude-opus-5") == "claude-opus-5"


# ──────────────────────────────── temperature ────────────────────────────────


def test_temperature_is_withheld_from_models_that_reject_it():
    """`AIRequest.temperature` defaults to 0.7, so every call would carry one.
    Sonnet 5 and Opus 5 removed the sampling parameters and answer 400 - not a
    warning - so sending it would fail every call in a run."""
    provider = AnthropicAPIProvider(default_model="sonnet", api_key="k")
    payload = provider._payload(_request(model="sonnet"))
    assert "temperature" not in payload


def test_temperature_is_sent_to_a_model_that_still_accepts_it():
    provider = AnthropicAPIProvider(default_model="haiku", api_key="k")
    payload = provider._payload(_request(model="haiku", temperature=0.2))
    assert payload["temperature"] == 0.2


def test_an_unknown_model_is_assumed_modern_and_gets_no_temperature():
    """A dropped parameter degrades a result; a rejected one loses it. The
    picker accepts operator-typed slugs, so unknown is the common case."""
    provider = AnthropicAPIProvider(default_model="sonnet", api_key="k")
    payload = provider._payload(_request(model="claude-something-unreleased"))
    assert "temperature" not in payload


def test_openai_withholds_temperature_from_the_reasoning_family():
    provider = OpenAIAPIProvider(default_model="gpt-5.6-sol", api_key="k")
    payload = provider._payload(_request(model="gpt-5.6-sol"))
    assert "temperature" not in payload


# ───────────────────────────────── the prompt ────────────────────────────────


def test_the_system_prompt_is_cached():
    """Every craft call in a run resends the same role prompt and the same
    Evidence Ledger. Uncached, each one pays full input price for text that
    has not changed since the run started."""
    provider = AnthropicAPIProvider(default_model="sonnet", api_key="k")
    payload = provider._payload(_request(system_prompt="Ledger: E1, E2, E3"))
    assert payload["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert payload["system"][0]["text"] == "Ledger: E1, E2, E3"


def test_openai_puts_the_system_prompt_in_instructions():
    """Unlike the Codex CLI, which has no system channel at all and made
    `openai_provider` fold it into the user turn."""
    provider = OpenAIAPIProvider(default_model="gpt-5.6-sol", api_key="k")
    payload = provider._payload(_request(system_prompt="Be terse."))
    assert payload["instructions"] == "Be terse."


# ────────────────────────────────── tools ────────────────────────────────────


def test_research_tools_map_to_the_server_side_variants():
    provider = AnthropicAPIProvider(default_model="sonnet", api_key="k")
    payload = provider._payload(
        _request(tools=[ResearchTool.WEB_SEARCH, ResearchTool.WEB_FETCH])
    )
    assert [tool["name"] for tool in payload["tools"]] == ["web_search", "web_fetch"]


def test_openai_refuses_a_call_asking_for_web_fetch():
    """Never answer without a capability that was asked for. A research role
    that silently loses its web access returns confident invention, which is
    the failure this system is built to make impossible."""
    provider = OpenAIAPIProvider(default_model="gpt-5.6-sol", api_key="k")
    with pytest.raises(ProviderCallError) as caught:
        provider._payload(_request(tools=[ResearchTool.WEB_FETCH]))
    assert "web_fetch" in str(caught.value)
    assert caught.value.retryable is False


def test_openai_still_declares_only_web_search():
    """The refusal to pin a market role to a GPT model reads this. Moving to
    the API does not widen it."""
    provider = OpenAIAPIProvider(default_model="gpt-5.6-sol", api_key="k")
    assert provider.available_tools() == frozenset({ResearchTool.WEB_SEARCH})


# ────────────────────────────────── usage ────────────────────────────────────


def test_anthropic_usage_keeps_the_two_cache_fields_apart():
    """A run measured at 76 input tokens had really sent ~179,000, all of it
    under the cache fields. This provider caches deliberately, so the same
    undercount would land here if only `input_tokens` were read."""
    usage = anthropic_usage(
        _Usage(
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=9_000,
            cache_read_input_tokens=70_000,
        )
    )
    assert usage.billable_input_tokens == 79_100
    assert usage.total_tokens == 79_150


def test_openai_cached_tokens_are_moved_across_not_added():
    """`cached_tokens` is a SUBSET of `input_tokens` here. Adding rather than
    moving counts every cached call twice against the run's budget."""
    usage = openai_usage(
        _Usage(input_tokens=1_000, output_tokens=40, input_tokens_details=_Usage(cached_tokens=800))
    )
    assert usage.input_tokens == 200
    assert usage.cache_read_input_tokens == 800
    assert usage.billable_input_tokens == 1_000


def test_openai_usage_survives_a_response_with_no_usage_block():
    assert openai_usage(None).total_tokens == 0


# ──────────────────────────── failure classification ─────────────────────────


@pytest.mark.parametrize(
    ("status", "retryable"),
    [(401, False), (403, False), (400, False), (404, False), (429, True), (500, True), (529, True)],
)
def test_anthropic_failures_are_classified(status, retryable):
    """A 429 clears on its own and should be resent; a bad key will fail
    identically forever and resending it just spends the deadline."""
    error = anthropic_error(_Usage(status_code=status))
    assert error.retryable is retryable


@pytest.mark.parametrize(
    ("status", "retryable"),
    [(401, False), (400, False), (429, True), (503, True)],
)
def test_openai_failures_are_classified(status, retryable):
    assert openai_error(_Usage(status_code=status)).retryable is retryable


def test_a_failure_with_no_status_is_treated_as_transport():
    """A connection error carries no status and is exactly what a resend is
    for."""
    assert anthropic_error(RuntimeError("connection reset")).retryable is True
    assert openai_error(RuntimeError("connection reset")).retryable is True


# ──────────────────────────────── credentials ────────────────────────────────


def test_a_missing_anthropic_key_fails_loudly_rather_than_falling_back(monkeypatch):
    """The two modes cost wildly different amounts. A provider that quietly
    fell back to the CLI would make a deployment's bill a matter of which
    environment variable happened to be set."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = AnthropicAPIProvider(default_model="sonnet")
    with pytest.raises(ProviderCallError) as caught:
        provider._anthropic()
    assert "ANTHROPIC_API_KEY" in str(caught.value)
    assert caught.value.retryable is False


def test_a_missing_openai_key_fails_loudly(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIAPIProvider(default_model="gpt-5.6-sol")
    with pytest.raises(ProviderCallError) as caught:
        provider._openai()
    assert "OPENAI_API_KEY" in str(caught.value)


# ────────────────────────────── billing selection ────────────────────────────


def _routing_backends(billing: str, monkeypatch):
    from app.ai.factory import get_ai_provider
    from app.core.config import get_settings

    monkeypatch.setenv("AI_BILLING", billing)
    get_settings.cache_clear()
    get_ai_provider.cache_clear()
    try:
        return dict(get_ai_provider()._backends)
    finally:
        get_settings.cache_clear()
        get_ai_provider.cache_clear()


def test_api_billing_builds_the_metered_backends(monkeypatch):
    backends = _routing_backends("api", monkeypatch)
    assert {type(backend).__name__ for backend in backends.values()} == {
        "AnthropicAPIProvider",
        "OpenAIAPIProvider",
    }


def test_subscription_billing_builds_the_cli_backends(monkeypatch):
    backends = _routing_backends("subscription", monkeypatch)
    assert {type(backend).__name__ for backend in backends.values()} == {
        "ClaudeProvider",
        "OpenAIProvider",
    }


def test_the_default_is_the_subscription(monkeypatch):
    """Metered billing is opted into, never arrived at. The default has to be
    the one that cannot charge a card by surprise."""
    monkeypatch.delenv("AI_BILLING", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        assert get_settings().ai_billing == "subscription"
    finally:
        get_settings.cache_clear()
