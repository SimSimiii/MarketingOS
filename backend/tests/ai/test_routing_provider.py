"""Per-agent model choice makes one campaign a multi-vendor run.

The failure this guards against is not a crash. It is a run that succeeds while
routing a GPT-pinned role to Claude: the report would say the writer ran on GPT
and it would be false, and nothing downstream could tell.
"""

from collections.abc import AsyncIterator

import pytest

from app.ai.base import AIProvider, AIRequest, AIResponse, ResearchTool
from app.ai.models import ModelVendor
from app.ai.routing_provider import RoutingProvider


class _Spy(AIProvider):
    def __init__(self, name: str, tools: frozenset[ResearchTool] = frozenset()) -> None:
        self.name = name
        self.seen: list[str | None] = []
        self._tools = tools

    async def generate(self, request: AIRequest) -> AIResponse:
        self.seen.append(request.model)
        return AIResponse(content=self.name, model=request.model or "")

    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        self.seen.append(request.model)
        yield self.name

    def available_tools(self, model: str | None = None) -> frozenset[ResearchTool]:
        return self._tools

    def count_tokens(self, text: str) -> int:
        return len(text)


def _router() -> tuple[RoutingProvider, _Spy, _Spy]:
    claude = _Spy("claude", frozenset({ResearchTool.WEB_SEARCH, ResearchTool.WEB_FETCH}))
    openai = _Spy("openai", frozenset({ResearchTool.WEB_SEARCH}))
    provider = RoutingProvider(
        {ModelVendor.ANTHROPIC: claude, ModelVendor.OPENAI: openai},
        default_vendor=ModelVendor.ANTHROPIC,
    )
    return provider, claude, openai


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("model", "expected"),
    [("opus", "claude"), ("haiku", "claude"), ("gpt-5.6-sol", "openai"), ("gpt-5.5", "openai")],
)
async def test_each_model_reaches_the_vendor_that_bills_for_it(model, expected):
    provider, _, _ = _router()
    response = await provider.generate(AIRequest(model=model))
    assert response.content == expected


@pytest.mark.asyncio
async def test_one_run_can_span_both_vendors():
    """The whole point of the picker: the writer on GPT, the critic on
    Claude, inside a single campaign."""
    provider, claude, openai = _router()

    await provider.generate(AIRequest(model="gpt-5.6-sol", role="email_writer"))
    await provider.generate(AIRequest(model="opus", role="conversion_critic"))

    assert openai.seen == ["gpt-5.6-sol"]
    assert claude.seen == ["opus"]


@pytest.mark.asyncio
async def test_an_unrecognised_slug_falls_back_to_the_configured_vendor():
    provider, claude, _ = _router()
    await provider.generate(AIRequest(model="something-nobody-has-heard-of"))
    assert claude.seen == ["something-nobody-has-heard-of"]


@pytest.mark.asyncio
async def test_streams_are_routed_the_same_way():
    provider, _, openai = _router()
    chunks = [chunk async for chunk in provider.stream(AIRequest(model="gpt-5.6-sol"))]
    assert chunks == ["openai"]
    assert openai.seen == ["gpt-5.6-sol"]


def test_capabilities_are_answered_per_model_not_per_union():
    """A union would tell a market role that fetch is available because *some*
    backend has it, and the role would then be handed to one that does not."""
    provider, _, _ = _router()

    assert ResearchTool.WEB_FETCH in provider.available_tools("opus")
    assert ResearchTool.WEB_FETCH not in provider.available_tools("gpt-5.6-sol")


def test_a_vendor_without_a_backend_fails_rather_than_falling_back():
    """A silent fallback here is the worst failure available: the run would
    succeed on the wrong vendor and the ledger would record the right one."""
    claude = _Spy("claude")
    provider = RoutingProvider({ModelVendor.ANTHROPIC: claude})

    with pytest.raises(ValueError, match="not configured"):
        provider.available_tools("gpt-5.6-sol")


def test_the_default_vendor_must_have_a_backend():
    with pytest.raises(ValueError, match="no backend"):
        RoutingProvider({ModelVendor.ANTHROPIC: _Spy("claude")}, ModelVendor.OPENAI)
