"""Persisted LinkedIn work; the HTTP request only enqueues local execution.

Like campaign execution, the local runner requires a single long-lived process.
A durable queue/worker must replace launch() for ephemeral hosting.
"""
import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.ai.base import AIProvider, ResearchTool
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR
from app.knowledge.store import ArtifactScope, ArtifactStore
from app.market.linkedin import propose_criteria, search
from app.market.store import MarketStore
from app.marketing.linkedin import write_message
from app.models.linkedin import LinkedInRun
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession, RoleCall
from app.runtime.prompt_engine import get_prompt_engine
from app.runtime.work_limits import admitted_job, create_job_task
from app.schemas.linkedin import CriteriaRequest, MessageRequest, SearchRequest

logger = logging.getLogger(__name__)
_tasks: set[asyncio.Task] = set()


class LinkedInError(Exception):
    pass


#: The job kinds, keyed by the request that asks for one. A closed mapping
#: rather than isinstance branches, so adding a kind means adding a row.
_KINDS: dict[type, str] = {
    SearchRequest: "search",
    MessageRequest: "message",
    CriteriaRequest: "criteria",
}
#: What each kind cannot start without. Only the search goes to the open web;
#: the other two read the brand, so they need it compiled first.
_NEEDS_KNOWLEDGE = {
    "message": "Compile this brand's knowledge before writing a message.",
    "criteria": "Compile this brand's knowledge before proposing targeting criteria.",
}


@admitted_job
def launch(db: Session, brand_id: UUID, provider: AIProvider,
           request: SearchRequest | MessageRequest | CriteriaRequest) -> LinkedInRun:
    kind = _KINDS[type(request)]
    if kind == "search" and ResearchTool.WEB_SEARCH not in provider.available_tools():
        raise LinkedInError("The configured model provider cannot search the public web.")
    if (missing := _NEEDS_KNOWLEDGE.get(kind)) is not None:
        stored = ArtifactStore(db).load(ArtifactScope(brand_id=brand_id))
        if stored is None or not stored.artifacts.business.what_it_does.strip():
            raise LinkedInError(missing)
    row = LinkedInRun(brand_id=brand_id, kind=kind, active_key=str(brand_id),
                      request=request.model_dump(mode="json"))
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise LinkedInError("A LinkedIn job is already running for this brand. Refresh its status.") from exc
    db.refresh(row)
    task = create_job_task(run_job(db.get_bind(), row.id, provider))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return row


async def _work(model: ModelSession, db: Session, row: LinkedInRun) -> dict:
    """The one paid step this job exists for, chosen by kind and nothing else."""
    if row.kind == "search":
        found = await search(model, SearchRequest.model_validate(row.request))
        return found.model_dump(mode="json")

    stored = ArtifactStore(db).load(ArtifactScope(brand_id=row.brand_id))
    if stored is None:
        raise LinkedInError("Brand knowledge is no longer available.")
    if row.kind == "criteria":
        request = CriteriaRequest.model_validate(row.request)
        segment = None
        if request.segment_name:
            # A chosen audience is the better answer to "who buys this" than
            # anything the company's own pages say, which is the entire reason
            # the map exists. Missing is not an error: a map can be rebuilt
            # under a campaign, and a proposal from the knowledge base alone is
            # still a proposal.
            demand = MarketStore(db).latest_map(row.brand_id)
            segment = demand.named(request.segment_name) if demand is not None else None
        criteria = await propose_criteria(model, request, stored.artifacts, segment)
        return criteria.model_dump(mode="json")
    return await write_message(
        model, MessageRequest.model_validate(row.request), stored.artifacts,
    )


async def run_job(engine: Engine, run_id: UUID, provider: AIProvider) -> None:
    with Session(engine) as db:
        row = db.get(LinkedInRun, run_id)
        if row is None or row.state != "running":
            return
        def record(call: RoleCall) -> None:
            row.calls += 1
            row.input_tokens += call.billable_input_tokens
            row.output_tokens += call.output_tokens
            db.add(row)
            db.commit()
        model = ModelSession(provider, get_prompt_engine(PROMPTS_DIR), EventBus(),
                             ModelRouter(), f"linkedin:{row.id}", on_call=record)
        try:
            # Bound total local work, including transport retries.
            async with asyncio.timeout(600):
                row.result = await _work(model, db, row)
                row.state = "completed"
        except asyncio.CancelledError:
            row.state = "failed"
            row.error = "Server stopped before this job finished. Start a new job to retry."
            raise
        except Exception as exc:
            logger.exception("LinkedIn job %s failed", row.id)
            row.state = "failed"
            row.error = str(exc) or "The job timed out. Start a new job to retry."
        finally:
            row.active_key = None
            row.completed_at = datetime.now(UTC)
            db.add(row)
            db.commit()


def reap_linkedin_runs(engine: Engine) -> int:
    """Single-worker startup recovery, matching campaign startup recovery."""
    with Session(engine) as db:
        rows = db.exec(select(LinkedInRun).where(LinkedInRun.state == "running")).all()
        for row in rows:
            row.state = "failed"
            row.active_key = None
            row.error = "Server restarted before this job finished. Start a new job to retry."
            row.completed_at = datetime.now(UTC)
            db.add(row)
        db.commit()
        return len(rows)
