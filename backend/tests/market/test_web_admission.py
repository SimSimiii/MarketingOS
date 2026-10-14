"""Admission follows the routed research model, not the default vendor."""

import pytest

from app.ai.base import ResearchTool
from app.ai.models import ModelVendor
from app.ai.routing_provider import RoutingProvider
from app.services.market_service import MarketError, _require_search, _require_web
from tests.marketing.conftest import RoleScriptedProvider


class ToolProvider(RoleScriptedProvider):
    def __init__(self, tools):
        super().__init__()
        self.tools = frozenset(tools)

    def available_tools(self, model=None):
        return self.tools


@pytest.mark.parametrize("role", [
    "rival_scout", "proof_hunter", "audience_cartographer", "prospect_finder",
])
def test_openai_default_does_not_refuse_claude_research(role):
    provider = RoutingProvider(
        backends={
            ModelVendor.OPENAI: ToolProvider([ResearchTool.WEB_SEARCH]),
            ModelVendor.ANTHROPIC: ToolProvider(list(ResearchTool)),
        },
        default_vendor=ModelVendor.OPENAI,
    )
    _require_web(provider, role)


def test_default_vendor_capabilities_cannot_admit_an_unsupported_research_model():
    provider = RoutingProvider(
        backends={
            ModelVendor.OPENAI: ToolProvider(list(ResearchTool)),
            ModelVendor.ANTHROPIC: ToolProvider([]),
        },
        default_vendor=ModelVendor.OPENAI,
    )
    with pytest.raises(MarketError, match="cannot read the web"):
        _require_web(provider, "rival_scout")
    with pytest.raises(MarketError, match="cannot search the web"):
        _require_search(provider, "audience_researcher")
