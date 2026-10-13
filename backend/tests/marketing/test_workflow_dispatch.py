"""Deployment-path regressions. Real handlers, scripted providers, no cloud calls."""
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlmodel import Session, select

import step_handlers
from app.models.campaign_execution import CampaignExecution
from app.models.campaign_run_state import CampaignRunState
from app.models.enums import ExecutionStatus
from app.orchestration import workflow_dispatch as dispatch
from app.runtime.work_limits import WorkLimitError
from tests.marketing.test_stepped_runner import _campaign, provider, session  # noqa: F401


def test_warm_lambda_keeps_http_loop_but_uses_the_new_admission_context():
    import asyncio
    from contextvars import ContextVar
    marker = ContextVar("invocation")

    async def inspect():
        return asyncio.get_running_loop(), marker.get()

    token = marker.set("first")
    try:
        first_loop, first = step_handlers._run_async(inspect())
        marker.set("second")
        second_loop, second = step_handlers._run_async(inspect())
        assert first_loop is second_loop
        assert not first_loop.is_closed()
        assert (first, second) == ("first", "second")
    finally:
        marker.reset(token)


@pytest.fixture
def workflow(session, provider, monkeypatch):  # noqa: F811
    fake = Mock()
    monkeypatch.setenv("CAMPAIGN_WORKFLOW_ARN", "arn:aws:states:eu-west-3:123:stateMachine:campaign")
    monkeypatch.setattr(dispatch, "client", lambda: fake)
    monkeypatch.setattr(step_handlers, "engine", session.get_bind())
    monkeypatch.setattr(step_handlers, "get_ai_provider", lambda: provider)
    campaign = _campaign(session)
    run = dispatch.launch(campaign, provider, session.get_bind())
    return campaign, run, fake


def test_dispatch_persists_state_and_deterministic_workflow_name(session, workflow):  # noqa: F811
    campaign, run, fake = workflow
    state = session.exec(select(CampaignRunState)).one()
    assert state.request_snapshot["id"] == str(campaign.id)
    assert state.workflow_arn.endswith(str(run.id))
    assert fake.start_execution.call_args.kwargs["name"] == str(run.id)
    assert run.status == ExecutionStatus.RUNNING


def test_duplicate_campaign_is_refused_across_processes(session, provider, workflow):  # noqa: F811
    from app.services.campaign_service import CampaignAlreadyRunningError
    campaign, _, fake = workflow
    with pytest.raises(CampaignAlreadyRunningError):
        dispatch.launch(campaign, provider, session.get_bind())
    assert fake.start_execution.call_count == 1


def test_linkedin_campaign_completes_in_plan_and_replay_does_not_buy_again(session, provider, monkeypatch):  # noqa: F811
    import json

    from app.models.generated_asset import GeneratedAsset
    from tests.api.test_linkedin_campaign import CHANNEL, DRAFT
    monkeypatch.setenv("CAMPAIGN_WORKFLOW_ARN", "arn:aws:states:eu-west-3:123:stateMachine:campaign")
    monkeypatch.setattr(dispatch, "client", Mock)
    monkeypatch.setattr(step_handlers, "engine", session.get_bind())
    monkeypatch.setattr(step_handlers, "get_ai_provider", lambda: provider)
    campaign = _campaign(session)
    campaign.channel = CHANNEL
    campaign.request = "Write one LinkedIn message to Alice"
    session.add(campaign)
    session.commit()
    provider.set_default("linkedin_writer", json.dumps({"body": DRAFT}))
    run = dispatch.launch(campaign, provider, session.get_bind())
    result = step_handlers.plan({"execution_id": str(run.id)})
    step_handlers.plan({"execution_id": str(run.id)})
    step_handlers.finish(result)
    session.expire_all()
    assert session.get(CampaignExecution, run.id).status == ExecutionStatus.COMPLETED
    assert len(session.exec(select(GeneratedAsset)).all()) == 1
    assert provider.calls_by_role["linkedin_writer"] == 1


def test_actual_handlers_replay_same_position_without_spending_again(session, provider, workflow):  # noqa: F811
    from app.models.agent_execution import AgentExecution
    from app.models.execution_log import ExecutionLog
    from app.orchestration.live_broker import broker
    _, run, _ = workflow
    planned = step_handlers.plan({"execution_id": str(run.id)})
    step_handlers.plan({"execution_id": str(run.id)})
    broker._sequence.clear()  # The Craft Lambda has its own process-local broker.
    first = step_handlers.craft(planned)
    with Session(session.get_bind()) as db:
        before = db.exec(select(CampaignRunState)).one().model_calls
    replay = step_handlers.craft(planned)
    assert first == replay or first["next_position"] == replay["next_position"]
    with Session(session.get_bind()) as db:
        assert db.exec(select(CampaignRunState)).one().model_calls == before
    next_step = first
    while next_step["more"]:
        next_step = step_handlers.craft(next_step)
    step_handlers.finish(next_step)
    step_handlers.finish(next_step)
    session.expire_all()
    assert session.get(CampaignExecution, run.id).completed_at is not None
    assert session.get(CampaignExecution, run.id).total_input_tokens > 0
    logs = session.exec(select(ExecutionLog).where(ExecutionLog.campaign_execution_id == run.id)).all()
    assert len({row.sequence for row in logs}) == len(logs)
    roles = session.exec(select(AgentExecution).where(AgentExecution.campaign_execution_id == run.id)).all()
    assert len({row.sequence_order for row in roles}) == len(roles)


def test_interruption_keeps_accepted_emails_and_recovery_is_idempotent(session, workflow):  # noqa: F811
    from app.models.generated_asset import GeneratedAsset
    _, run, _ = workflow
    planned = step_handlers.plan({"execution_id": str(run.id)})
    step_handlers.craft(planned)
    event = {"execution_id": str(run.id), "step_error": {"Error": "States.Timeout"}}
    step_handlers.recover(event)
    step_handlers.recover(event)
    session.expire_all()
    assets = session.exec(select(GeneratedAsset)).all()
    assert len(assets) == 1
    assert assets[0].asset_metadata["sequence_review_pending"]
    assert session.get(CampaignExecution, run.id).result["run_status"] == "degraded"


def test_cancel_before_plan_calls_no_model_and_finishes(session, workflow):  # noqa: F811
    _, run, _ = workflow
    dispatch.cancel(session, run)
    step_handlers.plan({"execution_id": str(run.id)})
    session.expire_all()
    assert session.get(CampaignExecution, run.id).status == ExecutionStatus.CANCELLED
    assert session.exec(select(CampaignRunState)).one().model_calls == 0


def test_budget_survives_new_permit_instances(session, workflow):  # noqa: F811
    _, run, _ = workflow
    first = dispatch.DurablePermit(session.get_bind(), run.id)
    first.attempt()
    first.record_usage(4_000_000)
    with pytest.raises(WorkLimitError, match="model budget"):
        dispatch.DurablePermit(session.get_bind(), run.id).attempt()


def test_deadline_and_lambda_time_are_checked_before_calls(session, workflow):  # noqa: F811
    _, run, _ = workflow
    with pytest.raises(WorkLimitError, match="safe Lambda"):
        dispatch.DurablePermit(session.get_bind(), run.id, lambda: 150_000).attempt()
    state = session.exec(select(CampaignRunState)).one()
    state.deadline_at = datetime.now(UTC) - timedelta(seconds=1)
    session.add(state)
    session.commit()
    with pytest.raises(WorkLimitError, match="time budget"):
        dispatch.DurablePermit(session.get_bind(), run.id).attempt()


def test_workflow_recovers_every_task_failure_without_ambiguous_retries():
    import json
    definition = json.loads((Path(__file__).resolve().parents[2] / "campaign.asl.json").read_text())
    for name in ("Plan", "CraftEmail", "Finish"):
        state = definition["States"][name]
        assert state["Catch"][0]["Next"] == "Recover"
        assert state["Catch"][0]["ResultPath"] == "$.step_error"
        assert state["Retry"][0]["ErrorEquals"] == ["Lambda.TooManyRequestsException"]
