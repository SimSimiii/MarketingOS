import asyncio
from dataclasses import dataclass
from uuid import UUID

from app.marketing.cancellation import CancellationToken


@dataclass
class ExecutionHandle:
    task: asyncio.Task
    cancel_token: CancellationToken
    campaign_id: UUID


class ExecutionRegistry:
    """Tracks in-flight campaign runs for this process: what a cancel
    request should signal, and which campaigns already have a run in
    flight (so a second /start can't race the first into two concurrent
    runs of the same campaign).

    In-memory and process-local - correct for the MVP's single-worker
    deployment. A multi-worker deployment would need this backed by shared
    state (a DB column plus a message bus) instead of a dict.
    """

    def __init__(self) -> None:
        self._handles: dict[UUID, ExecutionHandle] = {}

    def register(
        self, execution_id: UUID, campaign_id: UUID, task: asyncio.Task, cancel_token: CancellationToken
    ) -> None:
        self._handles[execution_id] = ExecutionHandle(
            task=task, cancel_token=cancel_token, campaign_id=campaign_id
        )
        task.add_done_callback(lambda _: self._handles.pop(execution_id, None))

    def get(self, execution_id: UUID) -> ExecutionHandle | None:
        return self._handles.get(execution_id)

    def is_campaign_running(self, campaign_id: UUID) -> bool:
        return any(handle.campaign_id == campaign_id for handle in self._handles.values())

    def cancel(self, execution_id: UUID) -> bool:
        """Signal cancellation. Returns False when the execution isn't
        (or is no longer) running - the caller decides whether that's a 404
        or a no-op."""
        handle = self._handles.get(execution_id)
        if handle is None:
            return False
        handle.cancel_token.cancel()
        return True


#: Process-wide singleton, matching app.orchestration.live_broker.broker.
registry = ExecutionRegistry()
