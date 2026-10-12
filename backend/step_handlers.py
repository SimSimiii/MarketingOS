"""Lambda entry points for the campaign state machine.

Three handlers, one per state, each a thin shell around
`app.orchestration.stepped_runner`:

    plan     → how many emails this campaign will be
    craft    → writes the next one; the state machine calls it once per email
    finish   → sequence pass, report, assets

The division is by *duration*, not by topic. A `balanced` campaign budgets
itself 1200 seconds and `maximum` 2400, both past Lambda's 900-second ceiling,
but one email is 10 to 35 model calls - roughly four minutes - which fits with
room to spare. So the unit of work is one email, and the loop lives in Step
Functions where there is no timeout to exceed.

Each handler takes and returns a small JSON object. Nothing of the run itself
travels between them: the brief, the accepted copy and the outcomes are in
`CampaignRunState`, and the artifacts, corpus and market maps are reloaded from
their own tables. That is what keeps the payload far below Step Functions'
256 KB limit no matter how long the emails get.

`lifespan="off"` has no equivalent here because there is no ASGI app - but the
same reasoning applies and is worth stating: these handlers must never run
`init_db()` or `reap_orphaned_executions()`. The first would race concurrent
containers through `CREATE TABLE`; the second would mark every RUNNING
execution failed, which for a state machine mid-loop means killing the very run
this invocation was called to advance.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.ai.factory import get_ai_provider
from app.core.database import engine
from app.models.campaign_run_state import CampaignRunState
from app.orchestration import stepped_runner

logging.getLogger("marketingos").setLevel(os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("marketingos.step_handlers")


def _execution_id(event: dict[str, Any]) -> UUID:
    """The one field every state passes.

    Step Functions hands a state the previous state's output, so `craft`
    receives what `plan` returned and finds the id in the same place. A missing
    id is a wiring error in the state machine and should fail loudly rather
    than default to something.
    """
    raw = event.get("execution_id")
    if not raw:
        raise ValueError("The event carries no execution_id.")
    return UUID(str(raw))


def _run(step, event: dict[str, Any], context=None) -> dict[str, Any]:
    from app.models.campaign_execution import CampaignExecution
    from app.orchestration.workflow_dispatch import DurablePermit, execution_lock, recover
    from app.runtime.work_limits import current_work

    execution_id = _execution_id(event)
    with execution_lock(engine, execution_id), Session(engine) as session:
        execution = session.get(CampaignExecution, execution_id)
        if execution is None:
            raise ValueError("Execution not found")
        state = session.exec(select(CampaignRunState).where(
            CampaignRunState.execution_id == execution_id
        )).first()
        if execution.completed_at is not None:
            return {"execution_id": str(execution_id), "more": False, "status": str(execution.status)}
        if state is None:
            raise ValueError("Missing durable admission")
        if event.get("step_error") or state.cancel_requested:
            recover(session, execution_id)
            return {"execution_id": str(execution_id), "more": False, "status": "stopped"}
        position = int(event.get("next_position", 1))
        if step is stepped_runner.craft and position < state.next_position:
            return stepped_runner.StepResult(str(execution_id), state.next_position,
                state.total_positions, state.next_position <= state.total_positions).as_dict()
        if step is stepped_runner.craft and position != state.next_position:
            raise ValueError("Out-of-order craft position")
        if step is stepped_runner.plan and state.brief is not None:
            return stepped_runner.StepResult(str(execution_id), state.next_position,
                state.total_positions, state.next_position <= state.total_positions).as_dict()
        # An interrupted call is ambiguous and must not be bought a second time.
        if state.inflight_step:
            recover(session, execution_id, "A previous invocation was interrupted. Accepted emails were kept.")
            return {"execution_id": str(execution_id), "more": False, "status": "stopped"}
        state.inflight_step = f"{step.__name__}:{position}"
        session.add(state)
        session.commit()
        remaining = getattr(context, "get_remaining_time_in_millis", None)
        permit = DurablePermit(engine, execution_id, remaining)
        token = current_work.set(permit)
        try:
            result = asyncio.run(step(session, execution_id, get_ai_provider()))
            session.refresh(state)
            state.inflight_step = None
            session.add(state)
            session.commit()
            return result.as_dict()
        finally:
            current_work.reset(token)


def plan(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    return _run(stepped_runner.plan, event, context)


def craft(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    return _run(stepped_runner.craft, event, context)


def finish(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    return _run(stepped_runner.finish, event, context)


def recover(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    from app.orchestration.workflow_dispatch import execution_lock
    from app.orchestration.workflow_dispatch import recover as finalize
    payload = event.get("requestPayload", event)
    if payload.get("job_id"):
        from app.orchestration.background_jobs import fail
        fail(engine, UUID(payload["job_id"]))
        return {"status": "stopped"}
    detail = event.get("detail", {})
    if "executionArn" in detail:
        event = {"execution_id": detail["executionArn"].rsplit(":", 1)[-1]}
    execution_id = _execution_id(event)
    with execution_lock(engine, execution_id), Session(engine) as session:
        finalize(session, execution_id)
    return {"execution_id": str(execution_id), "more": False, "status": "stopped"}


def reconcile(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    from datetime import UTC, datetime, timedelta

    from botocore.exceptions import ClientError

    from app.models.campaign_execution import CampaignExecution
    from app.orchestration.background_jobs import reconcile as reconcile_background
    from app.orchestration.workflow_dispatch import client
    reconcile_background(engine)
    recovered = 0
    with Session(engine) as session:
        states = session.exec(select(CampaignRunState).join(
            CampaignExecution, CampaignRunState.execution_id == CampaignExecution.id
        ).where(CampaignExecution.completed_at.is_(None),
                CampaignRunState.created_at < datetime.now(UTC) - timedelta(minutes=2))).all()
        for state in states:
            if not state.workflow_arn:
                continue
            try:
                status = client().describe_execution(executionArn=state.workflow_arn)["status"]
            except ClientError as exc:
                if exc.response["Error"]["Code"] != "ExecutionDoesNotExist":
                    raise
                status = "MISSING"
            if status != "RUNNING":
                recover({"execution_id": str(state.execution_id)})
                recovered += 1
    return {"recovered": recovered}


def probe(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """IAM-only network/auth check. GET model catalogs; no generation or charges."""
    import json
    import urllib.error
    import urllib.request

    from app.ai.api_credentials import provider_key
    results = {}
    endpoints = {
        "anthropic": ("https://api.anthropic.com/v1/models", {
            "x-api-key": provider_key("anthropic-api-key", os.environ.get("ANTHROPIC_API_KEY", "")), "anthropic-version": "2023-06-01",
        }),
        "openai": ("https://api.openai.com/v1/models", {
            "Authorization": "Bearer " + provider_key("openai-api-key", os.environ.get("OPENAI_API_KEY", "")),
        }),
    }
    for vendor, (url, headers) in endpoints.items():
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as response:
                data = json.load(response)
                results[vendor] = {"status": response.status, "models": [m["id"] for m in data.get("data", [])]}
        except urllib.error.HTTPError as exc:
            results[vendor] = {"status": exc.code}
        except (OSError, ValueError) as exc:
            results[vendor] = {"error": type(exc).__name__}
    return results


def background(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    from app.orchestration.background_jobs import execute
    asyncio.run(execute(engine, UUID(event["job_id"]), get_ai_provider(), context))
    return {"job_id": event["job_id"]}
