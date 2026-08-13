from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import cast


@dataclass(frozen=True)
class Event:
    """Base for every runtime event. Concrete events add their own fields."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class AgentStarted(Event):
    agent_id: str = ""
    execution_id: str = ""


@dataclass(frozen=True)
class AgentFinished(Event):
    agent_id: str = ""
    execution_id: str = ""
    duration_ms: float = 0.0


@dataclass(frozen=True)
class AgentFailed(Event):
    agent_id: str = ""
    execution_id: str = ""
    error: str = ""


@dataclass(frozen=True)
class ModelCallStarted(Event):
    """Published the instant an agent hands its prompt to the provider.

    This is the only signal available while the longest part of a campaign
    happens: a single `generate()` can block for the better part of a
    minute, and without it a watching UI has nothing to show between
    AgentStarted and AgentFinished.
    """

    agent_id: str = ""
    execution_id: str = ""
    model: str = ""
    prompt_chars: int = 0


@dataclass(frozen=True)
class ModelCallFinished(Event):
    agent_id: str = ""
    execution_id: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: float = 0.0
    response_chars: int = 0
    #: Cached input, which with the Claude Code CLI is most of the input there
    #: is. Carried on the event so a watching UI can show what a call really
    #: consumed rather than the fraction that happened to be uncached.
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    cost_usd: float = 0.0

    @property
    def billable_input_tokens(self) -> int:
        return (
            self.input_tokens + self.cache_creation_input_tokens + self.cache_read_input_tokens
        )


@dataclass(frozen=True)
class MemoryUpdated(Event):
    key: str = ""
    execution_id: str | None = None


class EventBus:
    """Simple synchronous pub/sub. Handlers are called in subscription order for
    the exact event type published - no wildcards, no priorities, no async."""

    def __init__(self) -> None:
        self._subscribers: dict[type[Event], list[Callable[[Event], None]]] = defaultdict(list)

    def subscribe[E: Event](self, event_type: type[E], handler: Callable[[E], None]) -> None:
        """Handlers receive the concrete event type they subscribed to, which
        is what `publish` guarantees - the cast is the one place that fact
        cannot be expressed to the type checker."""
        self._subscribers[event_type].append(cast(Callable[[Event], None], handler))

    def publish(self, event: Event) -> None:
        for handler in self._subscribers.get(type(event), []):
            handler(event)
