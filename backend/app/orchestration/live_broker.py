import asyncio
from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass
from typing import Any, Final
from uuid import UUID

#: Put on a subscriber's queue to signal the stream is finished - distinct
#: from any real event dict, so the SSE endpoint can tell "done" from "data".
CLOSE: Final[object] = object()

#: Events kept per execution so a client that reconnects (or opens the page
#: mid-run) can be caught up from where it left off. A campaign emits a few
#: dozen events; this is generous enough that a reconnect within the window
#: never loses anything, and small enough to be irrelevant to memory.
_REPLAY_BUFFER = 500

#: How many executions keep a replay buffer at all. Without a cap the
#: history would grow for the lifetime of the process, one bucket per run
#: ever started. The oldest bucket is dropped when a new run needs one.
_MAX_TRACKED_EXECUTIONS = 20


@dataclass(frozen=True)
class LiveEvent:
    """One event with its position in this execution's stream.

    The id is what makes reconnection lossless: the SSE route sends it as
    the event's `id:` field, the browser hands it back as `Last-Event-ID`,
    and the broker replays everything after it.
    """

    id: int
    payload: dict[str, Any]


class ExecutionEventBroker:
    """Fan-out of live campaign-run events (phase changes, role
    progress, deliverables landing) to however many clients are watching one
    execution over SSE, plus a short replay buffer per execution.

    Process-local (in-memory) - correct for the MVP's single-worker
    deployment. A multi-worker deployment would need this backed by
    something shared (Redis pub/sub or similar) instead; nothing else in the
    live-view design depends on it staying in-process.
    """

    def __init__(self) -> None:
        self._queues: dict[UUID, list[asyncio.Queue]] = defaultdict(list)
        self._history: OrderedDict[UUID, deque[LiveEvent]] = OrderedDict()
        self._sequence: dict[UUID, int] = defaultdict(int)

    def subscribe(self, execution_id: UUID, after_id: int | None = None) -> asyncio.Queue:
        """Start receiving this execution's events.

        `after_id` (the client's Last-Event-ID) replays everything buffered
        since that point before any new event arrives, so a dropped
        connection costs the viewer nothing. The replay is queued before the
        subscription is registered, which keeps buffered and live events in
        order even if the run publishes something mid-call.
        """
        queue: asyncio.Queue = asyncio.Queue()
        if after_id is not None:
            for event in self._history.get(execution_id, ()):
                if event.id > after_id:
                    queue.put_nowait(event)
        self._queues[execution_id].append(queue)
        return queue

    def unsubscribe(self, execution_id: UUID, queue: asyncio.Queue) -> None:
        subscribers = self._queues.get(execution_id)
        if not subscribers or queue not in subscribers:
            return
        subscribers.remove(queue)
        if not subscribers:
            self._queues.pop(execution_id, None)

    def publish(self, execution_id: UUID, event: dict[str, Any]) -> LiveEvent:
        self._sequence[execution_id] += 1
        live_event = LiveEvent(id=self._sequence[execution_id], payload=event)
        self._buffer_for(execution_id).append(live_event)
        for queue in self._queues.get(execution_id, []):
            queue.put_nowait(live_event)
        return live_event

    def close(self, execution_id: UUID) -> None:
        for queue in self._queues.get(execution_id, []):
            queue.put_nowait(CLOSE)

    def last_event_id(self, execution_id: UUID) -> int:
        """Highest id published for this execution, 0 if none. Lets a client
        that loaded its history over HTTP tell the stream where to resume."""
        return self._sequence.get(execution_id, 0)

    def _buffer_for(self, execution_id: UUID) -> deque[LiveEvent]:
        buffer = self._history.get(execution_id)
        if buffer is None:
            buffer = deque(maxlen=_REPLAY_BUFFER)
            self._history[execution_id] = buffer
            self._evict_oldest_idle()
        self._history.move_to_end(execution_id)
        return buffer

    def _evict_oldest_idle(self) -> None:
        """Drop history for the least recently active runs once over the cap.

        Never evicts an execution someone is still watching: that would reset
        its sequence counter under a live subscriber and make replay ids
        collide. With every tracked run being watched there is nothing safe
        to drop, so the cap gives - concurrency is what bounds it then.
        """
        for execution_id in list(self._history):
            if len(self._history) <= _MAX_TRACKED_EXECUTIONS:
                return
            if self._queues.get(execution_id):
                continue
            self._history.pop(execution_id, None)
            self._sequence.pop(execution_id, None)


#: Process-wide singleton - the orchestrator publishes into it, the SSE route
#: subscribes from it. Deliberately not request-scoped: a campaign run
#: outlives any single HTTP request (see app.orchestration.execution_manager).
broker = ExecutionEventBroker()
