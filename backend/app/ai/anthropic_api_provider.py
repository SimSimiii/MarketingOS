"""AIProvider backed by the Anthropic Messages API, billed per token.

The deliberate opposite of `claude_provider.ClaudeProvider`, and the two must
never be confused:

    ClaudeProvider          drives the `claude` CLI, bills the operator's
                            subscription, and `_clean_env()` strips
                            ANTHROPIC_API_KEY so it can never silently switch.

    AnthropicAPIProvider    calls the HTTP API with an API key and bills a
                            card, per token, on every call.

Both exist because they answer different questions. A laptop has an
authenticated CLI and unmetered quota, so it uses the subscription. A Lambda
has neither a `$HOME` the CLI can write to nor a browser to complete an OAuth
flow, so it uses a key. `app.ai.factory` picks one from `Settings.ai_billing`
and nothing else in the system knows there is a choice.

The cost difference is not a rounding error - a `balanced` campaign is 10 to 35
model calls per email - so the selection is an explicit setting rather than a
fallback, and it is never inferred from whether a key happens to be present.
An unset key here raises; it does not quietly fall back to the CLI.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from typing import Any

from app.ai.base import (
    AIProvider,
    AIRequest,
    AIResponse,
    AIUsage,
    ProviderCallError,
    ResearchTool,
)

logger = logging.getLogger("marketingos.ai.anthropic_api")

#: The catalog stores CLI aliases (`haiku`, `sonnet`, ...) because the CLI
#: resolves them to its own latest version. The HTTP API does not: it wants a
#: full model id and 404s on an alias. One mapping, here, rather than a second
#: catalog - `app.ai.models` stays the single list of what may be routed to.
_ALIASES: dict[str, str] = {
    "haiku": "claude-haiku-4-5",
    "sonnet": "claude-sonnet-5",
    "opus": "claude-opus-5",
    "fable5": "claude-fable-5-1",
}

#: Models that still accept `temperature`. On Sonnet 5, Opus 5 and Fable 5.1
#: the sampling parameters were removed and sending one returns **400**, not a
#: warning - so a request carrying `AIRequest.temperature` (which defaults to
#: 0.7) would fail every call rather than be quietly ignored. Membership, not
#: exclusion: an unknown model is assumed modern and gets no temperature,
#: because a dropped parameter degrades a result while a rejected one loses it.
_ACCEPTS_TEMPERATURE: frozenset[str] = frozenset({"claude-haiku-4-5"})

#: Server-side tools: Anthropic runs the search or the fetch and returns the
#: final text, so there is no client tool loop here. The `_20260209` variants
#: carry dynamic filtering and are what the models in the catalog support.
_SERVER_TOOLS: dict[ResearchTool, dict[str, Any]] = {
    ResearchTool.WEB_SEARCH: {"type": "web_search_20260209", "name": "web_search"},
    ResearchTool.WEB_FETCH: {"type": "web_fetch_20260209", "name": "web_fetch"},
}


def resolve_model(model: str) -> str:
    """A catalog alias, or a full model id passed straight through."""
    return _ALIASES.get(model, model)


class AnthropicAPIProvider(AIProvider):
    """Per-token Anthropic access for hosts that cannot run the CLI."""

    def __init__(self, default_model: str, *, api_key: str | None = None) -> None:
        self._default_model = default_model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY") or ""
        self._client: Any | None = None

    # ------------------------------------------------------------------ setup

    def _anthropic(self) -> Any:
        """The SDK client, built on first use.

        Imported here rather than at module scope so that a machine running on
        the subscription never pays the import, and so a missing package
        surfaces at the call that needed it naming what to install - the same
        contract `factory.get_ai_provider` documents for the CLI backends.
        """
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise ProviderCallError(
                "ANTHROPIC_API_KEY is not set. The API provider bills per token and "
                "will not fall back to the subscription CLI - set the key, or set "
                "AI_BILLING=subscription to use the CLI.",
                retryable=False,
            )
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:  # pragma: no cover - packaging failure
            raise ProviderCallError(
                "The `anthropic` package is not installed. Install it with "
                "`pip install anthropic`.",
                retryable=False,
            ) from exc
        # Retries off: `ModelSession` already resends a call that failed in
        # transport, and two layers of backoff turn one slow failure into a
        # run that looks hung.
        self._client = AsyncAnthropic(api_key=self._api_key, max_retries=0, timeout=600.0)
        return self._client

    # --------------------------------------------------------------- contract

    def available_tools(self, model: str | None = None) -> frozenset[ResearchTool]:
        return frozenset(_SERVER_TOOLS)

    def count_tokens(self, text: str) -> int:
        """Rough approximation (~4 chars/token), matching `ClaudeProvider`.

        The API can count exactly via `messages.count_tokens`, but that is a
        network round trip and this is called synchronously while budgeting a
        run. The two providers agreeing matters more than either being precise:
        a budget that means one thing on a laptop and another on Lambda is a
        budget nobody can reason about.
        """
        return max(1, len(text) // 4)

    def _payload(self, request: AIRequest) -> dict[str, Any]:
        model = resolve_model(request.model or self._default_model)
        content: list[dict[str, Any]] = []
        if request.image is not None:
            import base64

            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": request.image.mime_type,
                        "data": base64.standard_b64encode(request.image.data).decode(),
                    },
                }
            )
        for message in request.messages:
            content.append({"type": "text", "text": message.content})

        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": request.max_tokens,
            "messages": [{"role": "user", "content": content}],
        }

        if request.system_prompt:
            # Cached, and this is the single largest cost lever in the product.
            # Every craft call in a run resends the same role prompt and the
            # same Evidence Ledger; without this each one pays full input price
            # for text that has not changed since the run started.
            payload["system"] = [
                {
                    "type": "text",
                    "text": request.system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        if model in _ACCEPTS_TEMPERATURE:
            payload["temperature"] = request.temperature

        if request.tools:
            payload["tools"] = [
                _SERVER_TOOLS[tool] for tool in dict.fromkeys(request.tools)
            ]

        return payload

    async def generate(self, request: AIRequest) -> AIResponse:
        client = self._anthropic()
        payload = self._payload(request)
        try:
            message = await client.messages.create(**payload)
        except Exception as exc:
            raise _as_call_error(exc) from exc

        if getattr(message, "stop_reason", None) == "refusal":
            # A safety decline is a 200 with no usable content. Not retryable:
            # the same prompt declines again, and a silent empty draft would
            # reach the gates as "the writer produced nothing".
            details = getattr(message, "stop_details", None)
            raise ProviderCallError(
                "The model declined this request"
                + (f" ({details.category})" if details is not None else "")
                + ".",
                retryable=False,
            )

        text = "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )
        return AIResponse(content=text, model=message.model, usage=_usage(message.usage))

    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        client = self._anthropic()
        payload = self._payload(request)
        try:
            async with client.messages.stream(**payload) as events:
                async for chunk in events.text_stream:
                    yield chunk
        except Exception as exc:
            raise _as_call_error(exc) from exc


def _usage(usage: Any) -> AIUsage:
    """Map the SDK's usage onto ours.

    The two cache fields are the point. `AIUsage` documents a run measured at
    76 input tokens that had really sent ~179,000, all of it under the cache
    fields - and this provider caches the system prompt deliberately, so the
    same undercount would land here if only `input_tokens` were read.
    """
    return AIUsage(
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
        cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
    )


def _as_call_error(exc: Exception) -> ProviderCallError:
    """Classify an SDK failure into retryable or not.

    The distinction is the whole value: a 429 or a 529 clears on its own and
    `ModelSession` should resend it, while a bad key or a rejected parameter
    will fail identically forever and resending it just spends the deadline.
    """
    status = getattr(exc, "status_code", None)
    if status is None:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)

    if status in (401, 403):
        return ProviderCallError(
            f"Anthropic rejected the API key ({status}). Check ANTHROPIC_API_KEY "
            "and its workspace permissions.",
            retryable=False,
        )
    if status == 400:
        return ProviderCallError(f"Anthropic rejected the request: {exc}", retryable=False)
    if status == 404:
        return ProviderCallError(
            f"Anthropic does not know that model: {exc}. The catalog stores CLI "
            "aliases; see _ALIASES in this module.",
            retryable=False,
        )
    if status == 429 or (isinstance(status, int) and status >= 500):
        return ProviderCallError(f"Anthropic is unavailable ({status}): {exc}", retryable=True)
    # A connection error carries no status and is exactly the case a resend
    # exists for.
    return ProviderCallError(f"Anthropic call failed: {exc}", retryable=status is None)
