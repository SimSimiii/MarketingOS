"""The one door out of the closed world, and the locks on it.

Every call in this system is a closed world - a role is handed exactly what it
needs and can invent nothing, which is what makes the evidence gate a property
of the output. The market-intelligence roles are the exception, and these
tests are the reason that exception is safe to have.
"""

import pytest

from app.ai.base import AIRequest, ResearchTool
from app.ai.claude_provider import _MAX_RESEARCH_TURNS, _MAX_TURNS, ClaudeProvider


@pytest.fixture
def provider() -> ClaudeProvider:
    return ClaudeProvider(default_model="sonnet")


def test_a_normal_call_gets_no_tools_at_all(provider: ClaudeProvider) -> None:
    """Everything that writes, judges or plans. A writer that could fetch a
    URL is a writer whose claims the evidence gate cannot vouch for."""
    options = provider._options(AIRequest(role="email_writer"), "system")

    assert options.allowed_tools == []
    assert options.permission_mode == "default"
    assert options.max_turns == _MAX_TURNS


def test_a_research_call_gets_exactly_what_it_asked_for(
    provider: ClaudeProvider,
) -> None:
    options = provider._options(
        AIRequest(role="rival_scout", tools=[ResearchTool.WEB_SEARCH]), "system"
    )

    assert options.allowed_tools == ["WebSearch"]
    assert options.max_turns == _MAX_RESEARCH_TURNS


def test_permissions_are_bypassed_only_for_the_tools_on_the_list(
    provider: ClaudeProvider,
) -> None:
    """Nothing is attached to this process's stdin, so a tool the CLI must ask
    a human about is a tool that hangs until the deadline. `bypassPermissions`
    is scoped by `allowed_tools` in the same breath - and on a campaign call
    the list is empty, so it grants nothing."""
    research = provider._options(
        AIRequest(tools=[ResearchTool.WEB_SEARCH, ResearchTool.WEB_FETCH]), "system"
    )
    campaign = provider._options(AIRequest(), "system")

    assert research.permission_mode == "bypassPermissions"
    assert set(research.allowed_tools) == {"WebSearch", "WebFetch"}
    assert "Read" not in research.allowed_tools
    assert "Bash" not in research.allowed_tools
    assert campaign.permission_mode == "default"


def test_duplicate_tools_are_asked_for_once(provider: ClaudeProvider) -> None:
    options = provider._options(
        AIRequest(
            tools=[ResearchTool.WEB_SEARCH, ResearchTool.WEB_SEARCH, ResearchTool.WEB_FETCH]
        ),
        "system",
    )
    assert options.allowed_tools == ["WebSearch", "WebFetch"]


def test_the_turn_budget_is_bounded_on_a_research_call(
    provider: ClaudeProvider,
) -> None:
    """With tools on, a turn is a search or a page fetch the operator pays
    for. This is the only place in the system that could spend real money
    without a phase deciding to."""
    assert _MAX_RESEARCH_TURNS > _MAX_TURNS
    assert _MAX_RESEARCH_TURNS <= 30


def test_a_caller_may_tighten_the_budget_but_the_default_is_per_kind(
    provider: ClaudeProvider,
) -> None:
    assert provider._options(AIRequest(max_turns=3), "system").max_turns == 3


def test_the_claude_provider_declares_what_it_can_offer(
    provider: ClaudeProvider,
) -> None:
    assert provider.available_tools() == frozenset(
        {ResearchTool.WEB_SEARCH, ResearchTool.WEB_FETCH}
    )
