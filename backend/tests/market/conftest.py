"""Doubles for the market layer.

Two of them, and the second is the interesting one.

The provider double answers by template, like the campaign suite's, and adds
what the market layer needs on top: it declares which `ResearchTool`s it can
offer, and it records which ones each call asked for. That is the property
worth testing here - a scan that quietly ran without web access returns
plausible competitors from memory, which nothing downstream can distinguish
from a real answer.

The crawler double serves canned pages. Competitor profiling deliberately
reads pages this process fetched rather than trusting a model's memory, so a
test that stubbed the *extraction* would be testing nothing: the whole design
is that the extraction is checked against the fetched text, and only a real
page can exercise that.
"""

import json
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest

from app.ai.base import AIProvider, AIRequest, AIResponse, AIUsage, ResearchTool
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR
from app.ingestion.documents import RawDocument, SourceType
from app.ingestion.exceptions import LoaderError
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import PromptEngine


class ScriptedProvider(AIProvider):
    """Answers each prompt template from its own queue."""

    def __init__(self, tools: frozenset[ResearchTool] | None = None) -> None:
        self.queues: dict[str, deque[str]] = defaultdict(deque)
        self.requests: list[AIRequest] = []
        self.calls: dict[str, int] = defaultdict(int)
        self._tools = (
            frozenset({ResearchTool.WEB_SEARCH, ResearchTool.WEB_FETCH})
            if tools is None
            else tools
        )

    def push(self, template: str, *payloads: object) -> "ScriptedProvider":
        self.queues[template].extend(
            payload if isinstance(payload, str) else json.dumps(payload)
            for payload in payloads
        )
        return self

    def tools_used_by(self, template: str) -> list[ResearchTool]:
        return [
            tool
            for request in self.requests
            if request.template == template
            for tool in request.tools
        ]

    def available_tools(self, model: str | None = None) -> frozenset[ResearchTool]:
        """One scripted capability set, whatever the model. These tests fix the
        provider's answer on purpose - what they exercise is how a role reacts
        to a capability it cannot have, not which vendor withheld it."""
        return self._tools

    async def generate(self, request: AIRequest) -> AIResponse:
        self.requests.append(request)
        key = request.template or request.role
        self.calls[key] += 1
        if not self.queues.get(key):
            raise AssertionError(f"No scripted response for template {key!r}")
        return AIResponse(
            content=self.queues[key].popleft(),
            model=request.model or "scripted-model",
            usage=AIUsage(input_tokens=10, output_tokens=5),
        )

    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        yield (await self.generate(request)).content

    def count_tokens(self, text: str) -> int:
        return len(text.split())


class ScriptedCrawler:
    """A `SiteCrawler` that serves canned pages instead of the network."""

    def __init__(self, pages: dict[str, list[tuple[str, str]]]) -> None:
        #: start url -> [(page url, markdown)]. A start url that is absent
        #: raises, exactly as the real crawler does for a site that will not
        #: answer - which is the case `RivalProfile.verified` exists for.
        self._pages = pages
        self.crawled: list[str] = []

    async def crawl(self, start_url: str) -> list[RawDocument]:
        self.crawled.append(start_url)
        if start_url not in self._pages:
            raise LoaderError(f"Failed to fetch '{start_url}'", url=start_url)
        return [
            RawDocument(
                content=body,
                source=url,
                source_type=SourceType.WEBSITE,
                fetched_at=datetime.now(UTC),
            )
            for url, body in self._pages[start_url]
        ]


@pytest.fixture
def provider() -> ScriptedProvider:
    return ScriptedProvider()


@pytest.fixture
def session(provider: ScriptedProvider) -> ModelSession:
    return ModelSession(
        provider=provider,
        prompt_engine=PromptEngine(PROMPTS_DIR),
        events=EventBus(),
        model_router=ModelRouter(),
        execution_id="test-market",
    )
