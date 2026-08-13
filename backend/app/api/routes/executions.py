import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import CampaignServiceDep
from app.models.enums import LogLevel
from app.orchestration.live_broker import CLOSE, broker
from app.schemas.campaign import (
    AgentExecutionRead,
    CampaignExecutionDetail,
    CampaignExecutionRead,
    CampaignResultRead,
    GeneratedAssetRead,
    RunningExecutionRead,
)
from app.schemas.execution_log import ExecutionLogRead, ExecutionTimeline
from app.services.campaign_service import CampaignService, ExecutionNotCancellableError

router = APIRouter(prefix="/executions", tags=["executions"])

#: Keeps idle SSE connections (and any intermediate proxy) from timing out
#: while nothing is happening between agent steps.
_HEARTBEAT_SECONDS = 15

#: What a log read returns by default: the story of the run, without the
#: per-model-call progress chatter the live view uses as a heartbeat.
_NON_DEBUG_LEVELS = [LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR]


def _assets(service: CampaignService, execution_id: UUID) -> list[GeneratedAssetRead]:
    assets = service.get_generated_assets(execution_id)
    return [
        GeneratedAssetRead.model_validate(asset)
        for asset in sorted(assets, key=lambda a: (a.asset_type, a.position))
    ]


@router.get("/running", response_model=list[RunningExecutionRead])
def list_running_executions(service: CampaignServiceDep) -> list[RunningExecutionRead]:
    """Every campaign run currently in flight. Declared before
    `/{execution_id}/...` so "running" is never read as an execution id."""
    return [
        RunningExecutionRead(
            **CampaignExecutionRead.model_validate(execution).model_dump(),
            campaign_name=campaign.name if campaign else "Unknown campaign",
            campaign_request=campaign.request if campaign else "",
        )
        for execution, campaign in service.list_running_executions()
    ]


@router.get("/{execution_id}/status", response_model=CampaignExecutionDetail)
def get_execution_status(
    execution_id: UUID, service: CampaignServiceDep
) -> CampaignExecutionDetail:
    execution = service.get_execution(execution_id)
    if execution is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Execution not found")
    return CampaignExecutionDetail(
        **CampaignExecutionDetail.model_validate(execution).model_dump(
            exclude={"agent_executions", "assets"}
        ),
        agent_executions=[
            AgentExecutionRead.model_validate(a) for a in service.get_agent_executions(execution_id)
        ],
        assets=_assets(service, execution_id),
    )


@router.get("/{execution_id}/result", response_model=CampaignResultRead)
def get_execution_result(execution_id: UUID, service: CampaignServiceDep) -> CampaignResultRead:
    execution = service.get_execution(execution_id)
    if execution is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Execution not found")
    return CampaignResultRead(
        **CampaignResultRead.model_validate(execution).model_dump(
            exclude={"agent_executions", "assets", "result"}
        ),
        agent_executions=[
            AgentExecutionRead.model_validate(a) for a in service.get_agent_executions(execution_id)
        ],
        assets=_assets(service, execution_id),
        result=execution.result,
    )


@router.get("/{execution_id}/assets", response_model=list[GeneratedAssetRead])
def get_execution_assets(
    execution_id: UUID, service: CampaignServiceDep
) -> list[GeneratedAssetRead]:
    """The deliverables, ready to copy and paste."""
    if service.get_execution(execution_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Execution not found")
    return _assets(service, execution_id)


@router.post("/{execution_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
def cancel_execution(execution_id: UUID, service: CampaignServiceDep) -> dict[str, str]:
    """Ask a running campaign to stop. Cooperative: the pipeline checks between
    steps, so the email currently being written finishes and everything up to
    that point is persisted - never a half-written execution."""
    execution = service.get_execution(execution_id)
    if execution is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Execution not found")
    try:
        service.cancel_execution(execution)
    except ExecutionNotCancellableError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return {"status": "cancelling"}


@router.get("/{execution_id}/logs", response_model=list[ExecutionLogRead])
def get_execution_logs(
    execution_id: UUID,
    service: CampaignServiceDep,
    agent_id: str | None = None,
    include_debug: bool = False,
    after_sequence: int | None = None,
    limit: int = 1000,
) -> list[ExecutionLogRead]:
    """This run's log lines, oldest first.

    `agent_id` narrows to one role's lane - that is what the live view's
    per-role panel opens. DEBUG lines (the model-call progress chatter) are
    excluded unless asked for, so the default read is the story of the run
    rather than its instrumentation.
    """
    if service.get_execution(execution_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Execution not found")
    logs = service.get_execution_logs(
        execution_id,
        agent_id=agent_id,
        levels=None if include_debug else _NON_DEBUG_LEVELS,
        after_sequence=after_sequence,
        limit=limit,
    )
    return [ExecutionLogRead.model_validate(log) for log in logs]


@router.get("/{execution_id}/timeline", response_model=ExecutionTimeline)
def get_execution_timeline(execution_id: UUID, service: CampaignServiceDep) -> ExecutionTimeline:
    """Everything that was broadcast for this run, replayed from the database.

    This is what makes the live view survive a reload: the page loads the
    timeline, then opens the stream from `last_event_id`, and sees the whole
    run rather than only what happens from now on.
    """
    if service.get_execution(execution_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Execution not found")
    events, last_event_id = service.get_execution_timeline(execution_id)
    return ExecutionTimeline(
        execution_id=execution_id,
        events=events,
        last_event_id=last_event_id,
        is_running=service.is_execution_running(execution_id),
    )


@router.get("/{execution_id}/stream")
async def stream_execution(execution_id: UUID, request: Request, service: CampaignServiceDep):
    """Server-Sent Events feed of a campaign run as it happens: what the system
    learned about the business, the campaign brief, each role taking its turn,
    every model call going out and coming back, what a cold reader thought of
    each draft, emails landing. Closes once the run reaches a terminal state.

    A client that already has some of the run - it reloaded, or its
    connection dropped and the browser reconnected - sends its position as
    `Last-Event-ID` (or `?after_event_id=`, for the page's first connection
    after loading the timeline over HTTP). Everything since is replayed
    before the first new event, so catching up never leaves a hole.

    If the execution is already finished by the time a client connects,
    sends one synthetic `execution_finished` event and closes - so a late
    subscriber doesn't hang forever waiting for events that already fired.
    """
    execution = service.get_execution(execution_id)
    if execution is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Execution not found")

    after_id = _resume_point(request)

    async def event_stream():
        if not service.is_execution_running(execution_id):
            yield _sse(
                {
                    "type": "execution_finished",
                    "execution_id": str(execution_id),
                    "status": execution.status.value,
                },
                event_id=broker.last_event_id(execution_id),
            )
            return

        queue = broker.subscribe(execution_id, after_id=after_id)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_SECONDS)
                except TimeoutError:
                    yield ": heartbeat\n\n"
                    continue
                if item is CLOSE:
                    break
                yield _sse(item.payload, event_id=item.id)
        finally:
            broker.unsubscribe(execution_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _resume_point(request: Request) -> int | None:
    """Where this client left off, from either the browser's own reconnect
    header or the explicit query parameter the page uses on first connect.
    A malformed value is treated as "no position" - a client that sends
    nonsense gets the live feed, never an error."""
    for raw in (request.headers.get("last-event-id"), request.query_params.get("after_event_id")):
        if raw:
            try:
                return int(raw)
            except ValueError:
                continue
    return None


def _sse(payload: dict, event_id: int | None = None) -> str:
    prefix = f"id: {event_id}\n" if event_id else ""
    return f"{prefix}data: {json.dumps(payload)}\n\n"
