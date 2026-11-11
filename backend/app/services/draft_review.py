"""Source review for operator-written email, using the brand's current material."""

import asyncio
import logging
import os
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Engine
from sqlmodel import Session, select

from app.ai.base import AIProvider
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR, get_settings
from app.knowledge.store import ArtifactScope, ArtifactStore, StoredArtifacts, fingerprint_documents
from app.marketing.briefs import EmailBrief
from app.marketing.email_copy import Email
from app.marketing.gates import GateReport
from app.marketing.grounding import ClaimReviewer
from app.models.background_job import BackgroundJob
from app.models.brand import Brand
from app.orchestration import background_jobs
from app.runtime.events import EventBus
from app.runtime.exceptions import ProviderError
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import get_prompt_engine
from app.runtime.work_limits import WorkLimitError, admitted_job, create_job_task
from app.schemas.brand import DraftReviewJobRead, DraftReviewRead, DraftReviewRequest

CATEGORY = "draft_review"
_tasks: set[asyncio.Task] = set()
logger = logging.getLogger(__name__)


def current_knowledge(db: Session, brand_id: UUID) -> StoredArtifacts:
    scope = ArtifactScope(brand_id=brand_id)
    store = ArtifactStore(db)
    stored = store.load(scope)
    if stored is None or stored.fingerprint != fingerprint_documents(store.source_documents(scope)):
        raise WorkLimitError("Compile the current brand sources before reviewing a draft.", 409)
    return stored


def snapshot(job: BackgroundJob) -> DraftReviewJobRead:
    return DraftReviewJobRead(
        id=job.id, state=job.status["state"], result=job.status.get("result"),
        error=job.status.get("error") or job.status.get("message", ""),
    )


@admitted_job
def launch(
    db: Session, brand: Brand, provider: AIProvider, request: DraftReviewRequest,
) -> DraftReviewJobRead:
    if get_settings().credit_billing_enabled:
        raise WorkLimitError("Draft review is unavailable in credit billing mode.", 409)
    current_knowledge(db, brand.id)
    if db.exec(select(BackgroundJob.id).where(
        BackgroundJob.brand_id == brand.id, BackgroundJob.category == CATEGORY, BackgroundJob.active,
    )).first() is not None:
        raise WorkLimitError("A draft review is already running for this brand.")
    job = BackgroundJob(
        brand_id=brand.id, owner_id=brand.owner_id, action="launch", category=CATEGORY,
        payload=request.model_dump(mode="json"), status={"state": "running"}, claimed=True,
    )
    db.add(job)
    db.commit()
    state = snapshot(job)
    task = create_job_task(run_job(db.get_bind(), job.id, provider, distributed=False))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return state


async def run_job(engine: Engine, job_id: UUID, provider: AIProvider, *, distributed: bool) -> None:
    try:
        with Session(engine) as db:
            job = db.get(BackgroundJob, job_id)
            if job is None or not job.active:
                return
            data = DraftReviewRequest.model_validate(job.payload)
            stored = current_knowledge(db, job.brand_id)
            corpus = ArtifactStore(db).corpus_for(ArtifactScope(brand_id=job.brand_id))
        runtime = ModelSession(
            provider, get_prompt_engine(PROMPTS_DIR), EventBus(), ModelRouter(), f"draft-review:{job_id}",
        )
        async with asyncio.timeout(180):
            report = await ClaimReviewer(runtime).review(
                email=Email(position=1, subject="", preview_text="", greeting="", body=data.text,
                            call_to_action="", sign_off=""),
                brief=EmailBrief(position=1, next_step_url=str(data.destination or "")),
                artifacts=stored.artifacts, corpus=corpus, hints=GateReport(), pasted_text=data.text,
            )
        receipt = report.semantic_review or {}
        result = DraftReviewRead(
            approved=report.passed,
            decision=receipt.get("display_decision", receipt.get("decision")),
            issues=report.issues,
            sources=receipt.get("sources", {}),
        )
        status = DraftReviewJobRead(id=job_id, state="completed", result=result)
    except (ProviderError, TimeoutError):
        status = DraftReviewJobRead(id=job_id, state="failed", error="The AI source reviewer did not finish.")
    except WorkLimitError as exc:
        status = DraftReviewJobRead(id=job_id, state="failed", error=str(exc))
    except asyncio.CancelledError:
        status = DraftReviewJobRead(id=job_id, state="failed", error="The review was interrupted.")
        background_jobs.persist(engine, job_id, status, finished=True, refund_empty=distributed)
        raise
    except Exception:
        logger.exception("Draft review %s failed", job_id)
        status = DraftReviewJobRead(id=job_id, state="failed", error="The draft could not be reviewed.")
    background_jobs.persist(engine, job_id, status, finished=True, refund_empty=distributed)


def reap_local_draft_reviews(engine: Engine) -> None:
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return
    with Session(engine) as db:
        for job in db.exec(select(BackgroundJob).where(BackgroundJob.category == CATEGORY, BackgroundJob.active)):
            job.status = {"state": "failed", "error": "Server restarted. Run a new draft review if needed."}
            job.active = False
            job.completed_at = datetime.now(UTC)
            job.payload = {}
            db.add(job)
        db.commit()
