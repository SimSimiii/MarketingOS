"""Persisted, quota-admitted cold reads; deterministic checks are free."""
import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.ai.base import AIProvider
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR, get_settings
from app.marketing.email_analysis import analyse, as_email
from app.marketing.reader import BlindReader
from app.models.email_analysis import EmailAnalysis
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession, RoleCall
from app.runtime.prompt_engine import get_prompt_engine
from app.runtime.work_limits import admitted_job, create_job_task
from app.schemas.email_analysis import AnalysisReader, EmailAnalysisRequest, EmailAnalysisResult
from app.services.market_service import MarketService

logger = logging.getLogger(__name__)
_tasks: set[asyncio.Task] = set()


class EmailAnalysisError(ValueError):
    pass


def validate_request(db: Session, brand_id: UUID, request: EmailAnalysisRequest) -> None:
    if not request.subject.strip() or not request.body.strip():
        raise EmailAnalysisError("Supply a subject and email body.")
    if request.cold_read and get_settings().credit_billing_enabled:
        raise EmailAnalysisError("Cold reads are unavailable in credit billing mode.")


def _save(db: Session, brand_id: UUID, request: EmailAnalysisRequest, *, commit: bool = True) -> EmailAnalysis:
    artifacts = MarketService(db).artifacts_for(brand_id)
    result = analyse(request, artifacts)
    row = EmailAnalysis(brand_id=brand_id, request=request.model_dump(mode="json"),
                        result=result.model_dump(mode="json"),
                        active_key=str(brand_id) if request.cold_read else None,
                        state="running" if request.cold_read else "completed",
                        completed_at=None if request.cold_read else datetime.now(UTC))
    db.add(row)
    try:
        db.commit() if commit else db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise EmailAnalysisError("An email analysis is already running for this brand.") from exc
    db.refresh(row)
    return row


def checks(db: Session, brand_id: UUID, request: EmailAnalysisRequest) -> EmailAnalysis:
    validate_request(db, brand_id, request)
    return _save(db, brand_id, request.model_copy(update={"cold_read": False}))


@admitted_job
def launch(db: Session, brand_id: UUID, provider: AIProvider, request: EmailAnalysisRequest) -> EmailAnalysis:
    validate_request(db, brand_id, request)
    row = _save(db, brand_id, request)
    task = create_job_task(run_job(db.get_bind(), row.id, provider))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return row


async def run_job(engine: Engine, run_id: UUID, provider: AIProvider) -> None:
    with Session(engine) as db:
        row = db.get(EmailAnalysis, run_id)
        if row is None or row.state != "running":
            return

        def record(call: RoleCall) -> None:
            row.calls += 1
            row.input_tokens += call.billable_input_tokens
            row.output_tokens += call.output_tokens
            db.add(row)
            db.commit()

        model = ModelSession(provider, get_prompt_engine(PROMPTS_DIR), EventBus(), ModelRouter(),
                             f"email-analysis:{row.id}", on_call=record)
        try:
            request = EmailAnalysisRequest.model_validate(row.request)
            result = EmailAnalysisResult.model_validate(row.result)
            async with asyncio.timeout(300):
                # A cold reader sees identity/situation, never the brand's facts,
                # desired conclusion, objective or analysis from other checks.
                persona = request.audience.strip() or "a reader whose situation is unspecified; do not invent a job or prior experience"
                panel = await BlindReader(model).read(as_email(request), [persona])
                read = panel.reads[0]
                result.reader = AnalysisReader(
                    reported=read.reported, understood=read.understood if read.reported else None,
                    what_it_sells=read.what_it_sells, biggest_doubt=read.biggest_doubt,
                    stopped_at=read.stopped_at, would_act=read.would_act if read.reported else None,
                    situation_matches=read.situation_matches if request.audience.strip() else None,
                    relevance_feedback=read.relevance_feedback,
                    fixes=list(dict.fromkeys([*read.fixes, *([read.to_click_it_would_have_to] if read.to_click_it_would_have_to else [])])),
                    assessment=read.pull if read.reported else None,
                )
                result.coverage.append("One simulated reader; assessment is uncalibrated and does not estimate clicks or conversion. Forecast assumes one valid response; schema repair and transport retries may add calls.")
                row.result = result.model_dump(mode="json")
                row.state = "completed" if read.reported else "degraded"
        except asyncio.CancelledError:
            row.state = "degraded"
            row.error = "Analysis interrupted. The saved deterministic checks remain available."
            raise
        except Exception:
            logger.exception("Email analysis %s failed", row.id)
            row.state = "degraded"
            row.error = "The cold read could not finish. The saved deterministic checks remain available."
        finally:
            row.active_key = None
            row.completed_at = datetime.now(UTC)
            db.add(row)
            db.commit()


def reap_email_analyses(engine: Engine) -> None:
    with Session(engine) as db:
        for row in db.exec(select(EmailAnalysis).where(EmailAnalysis.state == "running")):
            row.state, row.active_key = "degraded", None
            row.error = "Server restarted. Saved checks remain available; run a new cold read if needed."
            row.completed_at = datetime.now(UTC)
            db.add(row)
        db.commit()
