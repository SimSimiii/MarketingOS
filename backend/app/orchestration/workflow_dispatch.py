"""Durable admission and dispatch for the Standard Step Functions workflow."""
import json
import os
import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import text, update
from sqlmodel import Session, select

from app.core.config import get_settings
from app.marketing.policy import resolve_policy
from app.models.campaign import Campaign
from app.models.campaign_execution import CampaignExecution
from app.models.campaign_run_state import CampaignRunState
from app.models.enums import ExecutionStatus, UserStatus
from app.models.user import User
from app.runtime.work_limits import WorkLimitError

_local_lock = threading.Lock()


def enabled():
    return bool(os.environ.get("CAMPAIGN_WORKFLOW_ARN"))


def client():
    import boto3
    from botocore.config import Config
    return boto3.client("stepfunctions", config=Config(
        connect_timeout=3, read_timeout=8, retries={"total_max_attempts": 1},
    ))


@contextmanager
def admission_lock(engine):
    # Session-level lock survives the observer's commits. No long transaction
    # encloses model work: this connection lives only during HTTP dispatch.
    if engine.dialect.name == "postgresql":
        with engine.connect() as connection:
            acquired = connection.execute(text("SELECT pg_try_advisory_lock(1297040207)")).scalar()
            if not acquired:
                raise WorkLimitError("Another job is being admitted. Please retry shortly.")
            try:
                yield
            finally:
                connection.execute(text("SELECT pg_advisory_unlock(1297040207)"))
    else:
        with _local_lock:
            yield


def launch(campaign, ai_provider, engine, **kwargs):
    from app.services.campaign_service import CampaignAlreadyRunningError

    if campaign.channel:
        raise WorkLimitError("The distributed workflow currently accepts email campaigns only.", 422)
    settings = get_settings()
    if settings.credit_billing_enabled:
        raise WorkLimitError("Credit billing is not enabled for distributed jobs.", 503)
    with admission_lock(engine), Session(engine) as db:
        running = db.exec(select(CampaignExecution).where(
            CampaignExecution.status.in_([ExecutionStatus.RUNNING, ExecutionStatus.PENDING])
        )).all()
        if any(row.campaign_id == campaign.id for row in running):
            raise CampaignAlreadyRunningError("This campaign already has a run in progress.")
        from app.models.background_job import BackgroundJob
        background = db.exec(select(BackgroundJob).where(BackgroundJob.active)).all()
        owners = [db.get(Campaign, row.campaign_id).owner_id for row in running] + [job.owner_id for job in background]
        if len(owners) >= settings.max_concurrent_jobs or owners.count(campaign.owner_id) >= settings.max_jobs_per_account:
            raise WorkLimitError("The maximum number of running jobs has been reached.")
        now = datetime.now(UTC)
        period = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        user = db.get(User, campaign.owner_id) if campaign.owner_id else None
        if user:
            if user.status == UserStatus.SUSPENDED:
                raise WorkLimitError("This account is unavailable.", 403)
            if user.quota_reset_at is None or user.quota_reset_at.replace(tzinfo=UTC) < period:
                user.runs_used = 0
                user.quota_reset_at = period
            if user.monthly_run_quota and user.runs_used >= user.monthly_run_quota:
                raise WorkLimitError("Monthly job quota reached.")
            user.runs_used += 1
            db.add(user)
        policy = resolve_policy((campaign.policy or {}).get("preset"), {
            k: v for k, v in (campaign.policy or {}).items() if k != "preset"
        } or None)
        execution = CampaignExecution(
            campaign_id=campaign.id, status=ExecutionStatus.RUNNING, started_at=now, **kwargs,
        )
        db.add(execution)
        state = CampaignRunState(
            execution_id=execution.id,
            request_snapshot=campaign.model_dump(mode="json"),
            deadline_at=now + timedelta(seconds=policy.max_duration_seconds),
        )
        arn = os.environ["CAMPAIGN_WORKFLOW_ARN"]
        state.workflow_arn = arn.replace(":stateMachine:", ":execution:") + ":" + str(execution.id)
        db.add(state)
        db.commit()
        from app.orchestration.campaign_orchestrator import CampaignOrchestrator
        CampaignOrchestrator(db, ai_provider)._emitter_for(execution.id).emit(
            "execution_started", "Campaign queued for preparation.",
            data={"campaign_id": str(campaign.id)},
        )
        try:
            client().start_execution(
                stateMachineArn=arn, name=str(execution.id),
                input=json.dumps({"execution_id": str(execution.id)}, sort_keys=True),
            )
        except Exception as exc:
            # An HTTP timeout does not prove that StartExecution failed. Keep
            # this admission and let reconciliation describe the named run.
            from botocore.exceptions import ClientError
            if isinstance(exc, ClientError) and exc.response["Error"]["Code"] not in {
                "ExecutionAlreadyExists", "ThrottlingException", "ServiceUnavailable",
            }:
                execution.status = ExecutionStatus.FAILED
                execution.completed_at = datetime.now(UTC)
                execution.error_message = "The workflow could not be started."
                db.add(execution)
                if user:
                    user.runs_used = max(0, user.runs_used - 1)
                    db.add(user)
                db.commit()
                raise WorkLimitError("The workflow could not be started. Please retry.", 503) from exc
        db.refresh(execution)
        db.expunge(execution)
        return execution


def cancel(db, execution):
    from app.services.campaign_service import ExecutionNotCancellableError
    if execution.completed_at is not None:
        raise ExecutionNotCancellableError("This execution is no longer running.")
    changed = db.execute(update(CampaignRunState).where(
        CampaignRunState.execution_id == execution.id,
    ).values(cancel_requested=True))
    if changed.rowcount != 1:
        raise ExecutionNotCancellableError("No distributed run state was found.")
    db.commit()


class DurablePermit:
    """Model-call accounting survives every process boundary."""
    def __init__(self, engine, execution_id: UUID, remaining=None):
        self.engine, self.execution_id, self.remaining = engine, execution_id, remaining

    def attempt(self):
        with Session(self.engine) as db:
            state = db.exec(select(CampaignRunState).where(
                CampaignRunState.execution_id == self.execution_id
            )).one()
            policy = resolve_policy(((state.request_snapshot or {}).get("policy") or {}).get("preset"), {
                k: v for k, v in ((state.request_snapshot or {}).get("policy") or {}).items() if k != "preset"
            } or None)
            if state.cancel_requested:
                raise WorkLimitError("The campaign was cancelled.")
            if state.deadline_at and datetime.now(UTC) >= state.deadline_at.replace(tzinfo=UTC):
                raise WorkLimitError("The campaign reached its time budget.")
            if self.remaining and self.remaining() < 210_000:
                raise WorkLimitError("The step reached its safe Lambda time budget.")
            changed = db.execute(update(CampaignRunState).where(
                CampaignRunState.id == state.id,
                CampaignRunState.model_calls < 500,
                CampaignRunState.model_tokens < policy.max_total_tokens,
            ).values(model_calls=CampaignRunState.model_calls + 1))
            db.commit()
            if changed.rowcount != 1:
                raise WorkLimitError("The campaign reached its model budget.")

    def record_usage(self, tokens):
        with Session(self.engine) as db:
            db.execute(update(CampaignRunState).where(
                CampaignRunState.execution_id == self.execution_id
            ).values(model_tokens=CampaignRunState.model_tokens + tokens))
            db.commit()


@contextmanager
def execution_lock(engine, execution_id):
    if engine.dialect.name == "postgresql":
        key = UUID(str(execution_id)).int % (2**63 - 1)
        with engine.connect() as connection:
            if not connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key}).scalar():
                raise WorkLimitError("This workflow step is already running.")
            try:
                yield
            finally:
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
    else:
        yield


def recover(db, execution_id, reason="A workflow step failed. Accepted emails were kept."):
    from app.orchestration.checkpoints import recover_accepted_emails
    execution = db.get(CampaignExecution, execution_id)
    if execution is None or execution.completed_at is not None:
        return
    state = db.exec(select(CampaignRunState).where(CampaignRunState.execution_id == execution_id)).first()
    delivered = recover_accepted_emails(db, execution)
    cancelled = state is not None and state.cancel_requested
    execution.status = ExecutionStatus.COMPLETED if delivered else (
        ExecutionStatus.CANCELLED if cancelled else ExecutionStatus.FAILED
    )
    execution.completed_at = datetime.now(UTC)
    execution.error_message = "Cancelled by the user." if cancelled else reason
    execution.result = {**(execution.result or {}), "run_status": "degraded" if delivered else (
        "cancelled" if cancelled else "failed"
    )}
    if state and state.model_calls == 0:
        campaign = db.get(Campaign, execution.campaign_id)
        user = db.get(User, campaign.owner_id) if campaign and campaign.owner_id else None
        period = state.created_at.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=UTC)
        if user and user.quota_reset_at and user.quota_reset_at.replace(tzinfo=UTC) == period:
            user.runs_used = max(0, user.runs_used - 1)
            db.add(user)
    if state:
        state.abort_reason = execution.error_message
        state.inflight_step = None
        db.add(state)
    db.add(execution)
    db.commit()
    # Use the same persisted/live event path as normal finalization.
    from app.ai.factory import get_ai_provider
    from app.orchestration.campaign_orchestrator import CampaignOrchestrator
    CampaignOrchestrator(db, get_ai_provider())._emitter_for(execution_id).emit(
        "execution_finished", execution.error_message,
        data={"status": execution.status.value, "run_status": execution.result["run_status"], "delivered": delivered},
    )
