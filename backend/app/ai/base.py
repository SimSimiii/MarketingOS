from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class AIMessage(BaseModel):
    """A single turn in a conversation sent to the model."""

    role: Literal["user", "assistant"]
    content: str


class ResearchTool(StrEnum):
    """A capability a call may reach for outside its own prompt.

    Named after the capability rather than after any vendor's tool, for the
    same reason roles ask for a model *tier* and never a model name: the
    provider owns the translation, and a second vendor moves one mapping.

    Everything else in this system is deliberately a closed world - a role is
    handed exactly what it needs and can invent nothing, which is what makes
    the evidence gate a property of the output rather than a hope. These two
    names are the only door out of it, and they exist because there is one
    question the closed world cannot answer: what everybody *else* is saying.
    A company's own material can never contain its competitors' promises, and
    copy written without knowing them is copy that collides with them by
    accident.

    The door is narrow on purpose. No role in the campaign pipeline may pass
    these - only the market-intelligence roles, which write nothing a reader
    ever sees and whose every finding lands in the evidence ledger carrying
    the verbatim text and URL that support it, to be checked by exactly the
    same gate as everything the compiler found.
    """

    #: Search the web and read result snippets.
    WEB_SEARCH = "web_search"
    #: Fetch and read a specific URL the caller or the search already named.
    WEB_FETCH = "web_fetch"


class AIRequest(BaseModel):
    """Vendor-agnostic request. Providers translate this into their own SDK call."""

    system_prompt: str | None = None
    messages: list[AIMessage] = Field(default_factory=list)
    model: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.7
    #: Which reasoning role asked for this, and which prompt template the
    #: system prompt was rendered from (empty when the caller built it itself).
    #: Providers are free to ignore both - they carry no instruction - but they
    #: make a call attributable without pattern-matching on prompt text, which
    #: is what per-role routing, caching and any honest test double all need.
    #: One role can make several differently-shaped calls, so the template is
    #: the finer-grained of the two.
    role: str = ""
    template: str = ""
    #: Capabilities this call may use beyond generating text. Empty for every
    #: call that writes, judges or plans - see `ResearchTool` for why the list
    #: is short and who is allowed to pass it.
    #:
    #: A provider that cannot offer a requested capability must fail the call
    #: rather than answer without it: a research role that silently loses its
    #: web access does not return an error, it returns confident invention,
    #: which is the one failure mode this system is built to make impossible.
    tools: list[ResearchTool] = Field(default_factory=list)
    #: How many assistant turns one call may take. Only meaningful with tools:
    #: a text call has nothing to loop on. Left to the provider's own default
    #: when unset.
    max_turns: int | None = None


class AIUsage(BaseModel):
    """What one model call actually consumed.

    The three input fields are separate because they are priced differently
    and, far more importantly, because a provider that reports only
    `input_tokens` reports almost nothing. The Claude Code CLI puts nearly all
    of a call's input under the two cache fields: a run measured at 76 input
    tokens had really sent ~179,000, which made the campaign budget guard
    (ExecutionPolicy.max_total_tokens) a decoration and the cost shown to the
    user an undercount of roughly 40%.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    #: Input written into the prompt cache on this call - full price plus a
    #: surcharge, and the field that carries the bulk of a first call.
    cache_creation_input_tokens: int = 0
    #: Input served from the cache - an order of magnitude cheaper, and where
    #: repeated calls in one run land.
    cache_read_input_tokens: int = 0
    #: What the provider itself says this call cost, when it says anything.
    #: Preferred over our own arithmetic: the CLI knows its own price list,
    #: including discounts no table here can track.
    reported_cost_usd: float | None = None

    @property
    def billable_input_tokens(self) -> int:
        """Every input token the call consumed, however it was priced. This is
        what quota is spent on, and therefore what a budget must count."""
        return (
            self.input_tokens + self.cache_creation_input_tokens + self.cache_read_input_tokens
        )

    @property
    def total_tokens(self) -> int:
        return self.billable_input_tokens + self.output_tokens


class AIResponse(BaseModel):
    """Vendor-agnostic response returned to agents, regardless of provider."""

    content: str
    model: str
    usage: AIUsage = Field(default_factory=AIUsage)


class AIProvider(ABC):
    """Contract every AI backend (Claude, OpenAI, Gemini, local) must implement.

    Agents and the orchestrator depend only on this interface, so swapping the
    underlying model vendor never touches agent code.
    """

    @abstractmethod
    async def generate(self, request: AIRequest) -> AIResponse:
        """Send a request to the model and return a normalized response."""
        raise NotImplementedError

    @abstractmethod
    def stream(self, request: AIRequest) -> AsyncIterator[str]:
        """Send a request to the model and yield text chunks as they arrive."""
        raise NotImplementedError

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Estimate the token count of a piece of text for this provider."""
        raise NotImplementedError

    def available_tools(self, model: str | None = None) -> frozenset[ResearchTool]:
        """Which `ResearchTool`s this provider can actually offer.

        `model` is the model the call is about to go to. Providers backed by a
        single vendor ignore it - their answer is the same either way - but a
        provider that fans out across vendors cannot answer without it, and
        with per-agent model choice one campaign is routinely two vendors.

        Declared rather than attempted, so a caller that needs the web finds
        out before it spends anything - and, far more importantly, so a
        provider that cannot search never answers a research question anyway.
        A market scan run without web access does not come back empty; it
        comes back with plausible competitors the model remembered, which is
        indistinguishable from a real answer right up until a user reads it.

        Empty by default: a provider opts in to the door, it is never opened
        for it.
        """
        return frozenset()
