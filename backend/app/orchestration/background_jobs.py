"""Persisted asynchronous Lambda jobs. Function names are a closed allowlist."""
import asyncio
import json
import os
from datetime import UTC, datetime, timedelta

from pydantic import TypeAdapter
from sqlalchemy import update
from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.background_job import BackgroundJob
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.campaign_execution import CampaignExecution
from app.models.enums import ExecutionStatus, UserStatus
from app.models.user import User
from app.orchestration.workflow_dispatch import admission_lock
from app.runtime.work_limits import WorkLimitError

MARKET_ACTIONS = {
    "launch_scan": "scan", "launch_proof_hunt": "proof", "launch_audience_map": "audience",
    "launch_prospect_search": "prospects", "launch_audience_research": "audience_research",
    "launch_relevance_dossier": "relevance_dossier",
}


def enabled():
    from app.runtime.work_limits import is_job_host
    return bool(os.environ.get("BACKGROUND_FUNCTION_NAME")) and not is_job_host()


def supports(function):
    return ((function.__module__ == "app.services.market_service" and function.__name__ in MARKET_ACTIONS)
            or (function.__module__ == "app.services.knowledge_compilation" and function.__name__ == "start_compilation")
            or (function.__module__ in {"app.services.linkedin_service", "app.services.email_analysis_service"}
            and function.__name__ == "launch"))


def lambda_client():
    import boto3
    from botocore.config import Config
    return boto3.client("lambda", config=Config(connect_timeout=3, read_timeout=8,
                                                retries={"total_max_attempts": 1}))


def encode(status):
    if hasattr(status, "model_dump"):
        return status.model_dump(mode="json")
    return json.loads(TypeAdapter(type(status)).dump_json(status))


def decode(row):
    from app.services.knowledge_compilation import CompilationJob
    from app.services.market_service import JobStatus
    return (CompilationJob.model_validate(row.status) if row.category == "knowledge"
            else TypeAdapter(JobStatus).validate_python(row.status))


def enqueue(function, arguments):
    engine = arguments.get("engine") or arguments["db"].get_bind()
    with admission_lock(engine), Session(engine) as db:
        brand = arguments.get("brand") or db.get(Brand, arguments["brand_id"])
        if brand is None:
            raise WorkLimitError("Brand not found.", 404)
        active = db.exec(select(BackgroundJob).where(BackgroundJob.active)).all()
        if any(job.brand_id == brand.id for job in active):
            raise WorkLimitError("A job is already running for this brand.")
        campaigns = db.exec(select(CampaignExecution).where(
            CampaignExecution.status.in_([ExecutionStatus.RUNNING, ExecutionStatus.PENDING])
        )).all()
        owners = [job.owner_id for job in active] + [db.get(Campaign, row.campaign_id).owner_id for row in campaigns]
        settings = get_settings()
        if settings.credit_billing_enabled:
            raise WorkLimitError("Credit billing is not enabled for distributed jobs.", 503)
        if len(owners) >= settings.max_concurrent_jobs or owners.count(brand.owner_id) >= settings.max_jobs_per_account:
            raise WorkLimitError("The maximum number of running jobs has been reached.")
        now = datetime.now(UTC)
        period = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        user = db.exec(select(User).where(User.id == brand.owner_id).with_for_update()).first() if brand.owner_id else None
        if user:
            if user.status == UserStatus.SUSPENDED:
                raise WorkLimitError("Account unavailable.", 403)
            if user.quota_reset_at is None or user.quota_reset_at.replace(tzinfo=UTC) < period:
                user.runs_used, user.quota_reset_at = 0, period
            if user.monthly_run_quota and user.runs_used >= user.monthly_run_quota:
                raise WorkLimitError("Monthly job quota reached.")
            user.runs_used += 1
            db.add(user)
        name = function.__name__
        category = ("email_analysis" if function.__module__ == "app.services.email_analysis_service"
                    else "linkedin" if function.__module__ == "app.services.linkedin_service"
                    else "market" if name in MARKET_ACTIONS else "knowledge")
        from app.services.knowledge_compilation import CompilationJob
        from app.services.market_service import JobStatus
        if category in {"linkedin", "email_analysis"}:
            request = arguments["request"]
            if category == "linkedin":
                from app.models.linkedin import LinkedInRun
                from app.services.linkedin_service import validate_request
                kind = validate_request(db, brand.id, arguments["provider"], request)
                status = LinkedInRun(brand_id=brand.id, kind=kind, active_key=str(brand.id), request=request.model_dump(mode="json"))
                db.add(status)
            else:
                from app.services.email_analysis_service import _save, validate_request
                validate_request(db, brand.id, request)
                status = _save(db, brand.id, request, commit=False)
            payload = {"run_id": str(status.id)}
        else:
            status = (CompilationJob(state="running", brand_id=brand.id, brand_name=brand.name)
                      if category == "knowledge" else JobStatus(kind=MARKET_ACTIONS[name], brand_id=brand.id, brand_name=brand.name))
            status.say("Queued for processing")
            payload = {k: (v.model_dump(mode="json") if hasattr(v, "model_dump") else v)
                       for k, v in arguments.items() if k not in {"self", "brand", "brand_id", "provider", "engine", "brand_name"}}
        job = BackgroundJob(brand_id=brand.id, owner_id=brand.owner_id, action=name,
                            category=category, payload=payload, status=encode(status))
        db.add(job)
        db.commit()
        try:
            lambda_client().invoke(FunctionName=os.environ["BACKGROUND_FUNCTION_NAME"],
                                   InvocationType="Event", Payload=json.dumps({"job_id": str(job.id)}).encode())
        except Exception as exc:
            # Ambiguous dispatch is reconciled, never silently sent twice.
            from botocore.exceptions import ClientError
            if isinstance(exc, ClientError) and exc.response["Error"]["Code"] in {
                "AccessDeniedException", "ResourceNotFoundException", "InvalidParameterValueException",
            }:
                fail(engine, job.id, "The job could not be dispatched.")
                raise WorkLimitError("The job could not be dispatched.", 503) from exc
        if category in {"linkedin", "email_analysis"}:
            db.refresh(status)
            db.expunge(status)
        return status


def latest(category, brand_id=None):
    from app.core.database import engine
    with Session(engine) as db:
        query = select(BackgroundJob).where(BackgroundJob.category == category)
        if brand_id:
            query = query.where(BackgroundJob.brand_id == brand_id)
        rows = db.exec(query.order_by(BackgroundJob.created_at.desc())).all()
        by_brand = {}
        for row in rows:
            if row.brand_id not in by_brand:
                by_brand[row.brand_id] = decode(row)
        return by_brand


def persist(engine, job_id, status, *, finished=False):
    with Session(engine) as db:
        job = db.exec(select(BackgroundJob).where(BackgroundJob.id == job_id).with_for_update()).first()
        if job and job.active:
            job.status = encode(status)
            if finished:
                job.active = False
                job.completed_at = datetime.now(UTC)
                if job.model_calls == 0:
                    refund(db, job)
            db.add(job)
            db.commit()


def refund(db, job):
    user = db.exec(select(User).where(User.id == job.owner_id).with_for_update()).first() if job.owner_id else None
    period = job.created_at.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=UTC)
    if user and user.quota_reset_at and user.quota_reset_at.replace(tzinfo=UTC) == period:
        user.runs_used = max(0, user.runs_used - 1)
        db.add(user)


def fail(engine, job_id, message="The job was interrupted. Saved results remain available."):
    with Session(engine) as db:
        job = db.exec(select(BackgroundJob).where(BackgroundJob.id == job_id).with_for_update()).first()
        if job is None or not job.active:
            return
        job.status = {**job.status, "state": "failed", "message": message,
                      "finished_at": datetime.now(UTC).isoformat()}
        if job.category in {"linkedin", "email_analysis"}:
            from uuid import UUID

            from app.models.email_analysis import EmailAnalysis
            from app.models.linkedin import LinkedInRun
            model = LinkedInRun if job.category == "linkedin" else EmailAnalysis
            run = db.get(model, UUID(job.payload["run_id"]))
            if run and run.state == "running":
                run.state, run.error, run.active_key = ("degraded" if job.category == "email_analysis" else "failed"), message, None
                run.completed_at = datetime.now(UTC)
                db.add(run)
        if job.category == "market":
            job.status["error"] = message
        job.active = False
        job.completed_at = datetime.now(UTC)
        if job.model_calls == 0:
            refund(db, job)
        db.add(job)
        db.commit()


class Permit:
    scheduled = False
    def __init__(self, engine, job_id, remaining):
        self.engine, self.job_id, self.remaining = engine, job_id, remaining

    def attempt(self):
        with Session(self.engine) as db:
            job = db.get(BackgroundJob, self.job_id)
            if not job or not job.active or (self.remaining and self.remaining() < 210_000):
                raise WorkLimitError("This job reached its safe Lambda time budget.")
            changed = db.execute(update(BackgroundJob).where(
                BackgroundJob.id == self.job_id, BackgroundJob.model_calls < 500,
                BackgroundJob.model_tokens < 4_000_000,
            ).values(model_calls=BackgroundJob.model_calls + 1))
            db.commit()
            if changed.rowcount != 1:
                raise WorkLimitError("This job reached its model budget.")

    def record_usage(self, tokens):
        with Session(self.engine) as db:
            db.execute(update(BackgroundJob).where(BackgroundJob.id == self.job_id).values(
                model_tokens=BackgroundJob.model_tokens + tokens))
            db.commit()

    def finish(self):
        pass


async def execute(engine, job_id, provider, context):
    from app.runtime.work_limits import current_work
    from app.services import knowledge_compilation as knowledge
    from app.services import market_service as market
    with Session(engine) as db:
        changed = db.execute(update(BackgroundJob).where(
            BackgroundJob.id == job_id, BackgroundJob.active, ~BackgroundJob.claimed,
        ).values(claimed=True))
        db.commit()
        if changed.rowcount != 1:
            return
        job = db.get(BackgroundJob, job_id)
        brand = db.get(Brand, job.brand_id)
        token = current_work.set(Permit(engine, job_id, getattr(context, "get_remaining_time_in_millis", None)))
        try:
            if job.category in {"linkedin", "email_analysis"}:
                from uuid import UUID

                from app.models.email_analysis import EmailAnalysis
                from app.models.linkedin import LinkedInRun
                from app.services.email_analysis_service import run_job as analyse_job
                from app.services.linkedin_service import run_job
                run_id = UUID(job.payload["run_id"])
                runner = run_job if job.category == "linkedin" else analyse_job
                await runner(engine, run_id, provider)
                db.expire_all()
                model = LinkedInRun if job.category == "linkedin" else EmailAnalysis
                persist(engine, job_id, db.get(model, run_id), finished=True)
                return
            if job.category == "knowledge":
                knowledge.jobs.pop(brand.id, None)
                status = knowledge.start_compilation.__wrapped__(brand.id, engine, provider, brand.name)
                tasks = set(knowledge.tasks)
            else:
                market._jobs.pop(brand.id, None)
                payload = dict(job.payload)
                if payload.get("options"):
                    from app.market.demand import MapOptions
                    payload["options"] = MapOptions.model_validate(payload["options"])
                method = getattr(market.MarketService, job.action) if job.action in MARKET_ACTIONS else None
                if method is None:
                    raise ValueError("Unknown job action")
                status = method.__wrapped__(market.MarketService(db), brand, provider, engine, **payload)
                tasks = set(market._running)
            persist(engine, job_id, status)
            while tasks:
                done, tasks = await asyncio.wait(tasks, timeout=3)
                for task in done:
                    task.result()
                persist(engine, job_id, status)
            persist(engine, job_id, status, finished=True)
        except Exception:
            fail(engine, job_id)
            raise
        finally:
            current_work.reset(token)


def reconcile(engine):
    with Session(engine) as db:
        jobs = db.exec(select(BackgroundJob).where(
            BackgroundJob.active, BackgroundJob.created_at < datetime.now(UTC) - timedelta(minutes=20)
        )).all()
        for job in jobs:
            fail(engine, job.id)
