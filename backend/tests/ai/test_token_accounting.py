"""What a call actually consumed, and what it actually cost.

These exist because the answer used to be "nobody knows". The provider read
two fields out of the CLI's usage report and ignored the two that carry the
prompt, so a campaign that sent ~179,000 input tokens recorded 76. Everything
downstream inherited the lie: the cost on the user's screen was ~40% low, and
the token budget compared a real limit against a number several times too
small and could never fire.
"""

import pytest

from app.ai import claude_provider
from app.ai.base import AIMessage, AIRequest, AIUsage
from app.ai.claude_provider import ClaudeProvider
from app.ai.models import ClaudeModel, usage_cost_usd


class _FakeTextBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeAssistantMessage:
    def __init__(self, text: str) -> None:
        self.content = [_FakeTextBlock(text)]


class _FakeResultMessage:
    def __init__(self, usage: dict, cost: float | None = None) -> None:
        self.usage = usage
        self.total_cost_usd = cost
        self.result = None


def _install(monkeypatch, messages: list[object]) -> None:
    async def fake_query(prompt: str, options):
        for message in messages:
            yield message

    monkeypatch.setattr(claude_provider, "query", fake_query)
    monkeypatch.setattr(claude_provider, "AssistantMessage", _FakeAssistantMessage)
    monkeypatch.setattr(claude_provider, "TextBlock", _FakeTextBlock)
    monkeypatch.setattr(claude_provider, "ResultMessage", _FakeResultMessage)
    monkeypatch.setattr(claude_provider, "_needs_proactor_thread", lambda: False)


def _request() -> AIRequest:
    return AIRequest(
        system_prompt="You are terse.",
        messages=[AIMessage(role="user", content="Say OK")],
        model="opus",
    )


@pytest.mark.asyncio
async def test_cached_input_is_counted_not_discarded(monkeypatch):
    """The exact shape a real call comes back in: two uncached tokens beside
    a fully cached 31,000-character prompt."""
    _install(
        monkeypatch,
        [
            _FakeAssistantMessage("OK"),
            _FakeResultMessage(
                {
                    "input_tokens": 2,
                    "output_tokens": 800,
                    "cache_creation_input_tokens": 7_500,
                    "cache_read_input_tokens": 24_000,
                }
            ),
        ],
    )

    response = await ClaudeProvider(default_model="opus").generate(_request())

    assert response.usage.input_tokens == 2
    assert response.usage.cache_creation_input_tokens == 7_500
    assert response.usage.cache_read_input_tokens == 24_000
    # The number a budget has to be measured against.
    assert response.usage.billable_input_tokens == 31_502
    assert response.usage.total_tokens == 32_302


@pytest.mark.asyncio
async def test_the_providers_own_cost_is_kept_when_it_reports_one(monkeypatch):
    _install(
        monkeypatch,
        [
            _FakeAssistantMessage("OK"),
            _FakeResultMessage({"input_tokens": 2, "output_tokens": 10}, cost=0.4213),
        ],
    )

    response = await ClaudeProvider(default_model="opus").generate(_request())

    assert response.usage.reported_cost_usd == 0.4213


@pytest.mark.asyncio
async def test_a_provider_that_reports_no_usage_is_zero_not_a_crash(monkeypatch):
    _install(monkeypatch, [_FakeAssistantMessage("OK"), _FakeResultMessage({})])

    response = await ClaudeProvider(default_model="opus").generate(_request())

    assert response.usage.billable_input_tokens == 0
    assert response.usage.reported_cost_usd is None


def test_the_reported_cost_wins_over_our_price_table():
    """The provider knows its own price list, including plan rates and
    discounts no table in this repository can track."""
    usage = AIUsage(input_tokens=1_000_000, output_tokens=1_000_000, reported_cost_usd=0.02)

    assert usage_cost_usd(ClaudeModel.OPUS, usage) == 0.02


def test_cached_input_is_priced_as_cached_input():
    """Charging cache reads at full input price overstates exactly the calls
    this system makes most - the same writer prompt, sent again a minute
    later - and would make every optimization look less effective than it is."""
    fresh = AIUsage(input_tokens=100_000)
    cached = AIUsage(cache_read_input_tokens=100_000)

    fresh_cost = usage_cost_usd(ClaudeModel.OPUS, fresh)
    cached_cost = usage_cost_usd(ClaudeModel.OPUS, cached)

    assert fresh_cost == pytest.approx(1.5)
    assert cached_cost == pytest.approx(0.15)


def test_writing_to_the_cache_costs_more_than_plain_input():
    written = AIUsage(cache_creation_input_tokens=100_000)

    assert usage_cost_usd(ClaudeModel.OPUS, written) == pytest.approx(1.875)


def test_an_unknown_model_falls_back_instead_of_raising():
    assert usage_cost_usd("some-future-model", AIUsage(input_tokens=1_000)) == pytest.approx(
        0.003
    )
