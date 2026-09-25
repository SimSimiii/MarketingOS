"""AIProvider backed by the OpenAI Responses API, billed per token.

The counterpart of `anthropic_api_provider` for the GPT half of the catalog,
and the deliberate opposite of `openai_provider.OpenAIProvider`:

    OpenAIProvider          drives the `codex` binary, bills the operator's
                            ChatGPT plan, and `_clean_env()` strips
                            OPENAI_API_KEY so it can never silently switch.

    OpenAIAPIProvider       calls the HTTP API with a key and bills a card.

`app.ai.factory` picks one from `Settings.ai_billing`. A run routinely spans
both vendors - the writer on GPT and the critic on Claude is a supported
shape - so the billing mode is chosen once for the host and applies to both
vendors at the same time. Mixing a subscription CLI with a metered API inside
one run would make the cost of that run unanswerable.
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
from app.ai.models import OpenAIModel

logger = logging.getLogger("marketingos.ai.openai_api")

#: The same narrowing the CLI provider declares, for the same reason: OpenAI
#: offers hosted web search and nothing that fetches one named URL. It is why
#: `app/market` roles cannot be pinned to a GPT model - the refusal at save
#: time reads this, and moving to the API does not widen it.
_SUPPORTED_TOOLS = frozenset({ResearchTool.WEB_SEARCH})

#: Models that still accept `temperature`. The GPT-5 reasoning family rejects
#: sampling parameters, and `AIRequest.temperature` defaults to 0.7, so a
#: request would carry one to every call. Membership rather than exclusion, so
#: an unrecognised slug is treated as modern.
_ACCEPTS_TEMPERATURE: frozenset[str] = frozenset()


class OpenAIAPIProvider(AIProvider):
    """Per-token OpenAI access for hosts that cannot run the CLI."""

    def __init__(self, default_model: str = OpenAIModel.SOL, *, api_key: str | None = None) -> None:
        self._default_model = default_model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY") or ""
        self._client: Any | None = None

    def _openai(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise ProviderCallError(
                "OPENAI_API_KEY is not set. The API provider bills per token and will "
                "not fall back to the Codex CLI - set the key, or set "
                "AI_BILLING=subscription to use the CLI.",
                retryable=False,
            )
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover - packaging failure
            raise ProviderCallError(
                "The `openai` package is not installed. Install it with "
                "`pip install openai`.",
                retryable=False,
            ) from exc
        # Retries off for the same reason as the Anthropic provider:
        # `ModelSession` owns resending.
        self._client = AsyncOpenAI(api_key=self._api_key, max_retries=0, timeout=600.0)
        return self._client

    def available_tools(self, model: str | None = None) -> frozenset[ResearchTool]:
        return _SUPPORTED_TOOLS

    def count_tokens(self, text: str) -> int:
        """Same ~4 chars/token approximation as every other provider, so a
        budget means the same thing whichever vendor a role is routed to."""
        return max(1, len(text) // 4)

    def _payload(self, request: AIRequest) -> dict[str, Any]:
        model = request.model or self._default_model
        content: list[dict[str, Any]] = []
        if request.image is not None:
            import base64

            encoded = base64.standard_b64encode(request.image.data).decode()
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:{request.image.mime_type};base64,{encoded}",
                }
            )
        for message in request.messages:
            content.append({"type": "input_text", "text": message.content})

        payload: dict[str, Any] = {
            "model": model,
            "input": [{"role": "user", "content": content}],
            "max_output_tokens": request.max_tokens,
        }
        if request.system_prompt:
            # `instructions` is the Responses API's system channel. Unlike the
            # Codex CLI - which has no system prompt at all and made
            # `openai_provider` fold it into the user turn - this one has a
            # real place to put it.
            payload["instructions"] = request.system_prompt
        if model in _ACCEPTS_TEMPERATURE:
            payload["temperature"] = request.temperature
        if request.tools:
            unsupported = set(request.tools) - _SUPPORTED_TOOLS
            if unsupported:
                # Never answer without a capability that was asked for. A
                # research role that silently loses its web access does not
                # return an error, it returns confident invention - see
                # `ResearchTool`.
                raise ProviderCallError(
                    "OpenAI cannot provide "
                    f"{', '.join(sorted(tool.value for tool in unsupported))}.",
                    retryable=False,
                )
            payload["tools"] = [{"type": "web_search"}]
        return payload

    async def generate(self, request: AIRequest) -> AIResponse:
        client = self._openai()
        payload = self._payload(request)
        try:
            response = await client.responses.create(**payload)
        except Exception as exc:
            raise _as_call_error(exc) from exc

        text = getattr(response, "output_text", "") or ""
        return AIResponse(
            content=text,
            model=getattr(response, "model", payload["model"]),
            usage=_usage(getattr(response, "usage", None)),
        )

    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        client = self._openai()
        payload = self._payload(request)
        try:
            stream = await client.responses.create(**payload, stream=True)
            async for event in stream:
                if getattr(event, "type", "") == "response.output_text.delta":
                    yield getattr(event, "delta", "") or ""
        except Exception as exc:
            raise _as_call_error(exc) from exc


def _usage(usage: Any) -> AIUsage:
    """Map OpenAI's usage onto ours.

    `cached_tokens` is a **subset** of `input_tokens` here, not a sibling of
    it - the same trap `openai_provider._usage` documents for the CLI. `AIUsage`
    splits the two and sums them back in `billable_input_tokens`, so the cached
    part has to be moved across rather than added, or every cached call is
    counted twice against the run's budget.
    """
    if usage is None:
        return AIUsage()
    total_input = getattr(usage, "input_tokens", 0) or 0
    details = getattr(usage, "input_tokens_details", None)
    cached = (getattr(details, "cached_tokens", 0) or 0) if details is not None else 0
    cached = min(cached, total_input)
    return AIUsage(
        input_tokens=max(0, total_input - cached),
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
        cache_read_input_tokens=cached,
    )


def _as_call_error(exc: Exception) -> ProviderCallError:
    """Retryable or not - see `anthropic_api_provider._as_call_error`."""
    status = getattr(exc, "status_code", None)
    if status is None:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)

    if status in (401, 403):
        return ProviderCallError(
            f"OpenAI rejected the API key ({status}). Check OPENAI_API_KEY.",
            retryable=False,
        )
    if status == 400:
        return ProviderCallError(f"OpenAI rejected the request: {exc}", retryable=False)
    if status == 404:
        return ProviderCallError(f"OpenAI does not know that model: {exc}", retryable=False)
    if status == 429 or (isinstance(status, int) and status >= 500):
        return ProviderCallError(f"OpenAI is unavailable ({status}): {exc}", retryable=True)
    return ProviderCallError(f"OpenAI call failed: {exc}", retryable=status is None)
