"""Standalone compilation jobs; the last successful artifact stays available."""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer, field_validator
from sqlalchemy import Engine
from sqlmodel import Session

from app.ai.base import AIProvider
from app.ai.model_router import ModelRouter
from app.ai.roles import validate_overrides
from app.core.config import PROMPTS_DIR, get_settings
from app.knowledge.compiler import KnowledgeCompiler
from app.knowledge.store import ArtifactScope, ArtifactStore, build_corpus, fingerprint_documents
from app.models.brand import Brand
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession, RoleCall
from app.runtime.prompt_engine import get_prompt_engine
from app.runtime.work_limits import admitted_job, create_job_task

logger = logging.getLogger(__name__)


class CompilationStatus(BaseModel):
    state: Literal["idle", "running", "completed", "failed"] = "idle"
    message: str = ""


class CompilationRequest(BaseModel):
    model: str | None = Field(default=None, max_length=200)

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str | None) -> str | None:
        value = (value or "").strip()
        if not value:
            return None
        if get_settings().credit_billing_enabled:
            raise ValueError("Per-job model selection is unavailable with credit billing.")
        if value in {"fast", "balanced", "deep"}:
            raise ValueError("Choose a model name, not a tier.")
        return validate_overrides({"knowledge_compiler": value}).get("knowledge_compiler")


class CompilationJob(CompilationStatus):
    brand_id: UUID
    brand_name: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    log: list[str] = Field(default_factory=list)
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    @field_serializer("input_tokens", "output_tokens")
    def hide_tokens(self, value: int) -> int:
        return 0 if get_settings().credit_billing_enabled else value

    def say(self, message: str) -> None:
        self.message = message
        self.log.append(message)

    def record(self, call: RoleCall) -> None:
        self.calls += 1
        self.input_tokens += call.billable_input_tokens
        self.output_tokens += call.output_tokens
        if get_settings().credit_billing_enabled:
            self.log.append("Knowledge compiler · step completed")
            return
        self.log.append(
            f"Knowledge compiler · {call.model} · {call.duration_ms / 1000:.1f}s · "
            f"{call.billable_input_tokens:,} in / {call.output_tokens:,} out"
        )


# Like market jobs, these are process-local: a restart permits a fresh attempt.
jobs: dict[UUID, CompilationJob] = {}
tasks: set[asyncio.Task] = set()


@admitted_job
def start_compilation(
    brand_id: UUID, engine: Engine, provider: AIProvider, brand_name: str,
    model: str | None = None,
) -> CompilationJob:
    validate_overrides({"knowledge_compiler": model} if model else None)
    current = jobs.get(brand_id)
    if current is not None and current.state == "running":
        return current
    from app.runtime.work_limits import WorkLimitError
    from app.services.market_service import job_for as market_job_for

    market_job = market_job_for(brand_id)
    if market_job and market_job.kind == "first_campaign" and market_job.state == "running":
        raise WorkLimitError("First campaign preparation is already reading this brand.", 409)
    job = CompilationJob(state="running", brand_id=brand_id, brand_name=brand_name)
    job.say("Reading knowledge sources…")
    jobs[brand_id] = job
    task = create_job_task(_compile(brand_id, engine, provider, job, model))
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    return job


async def _compile(
    brand_id: UUID, engine: Engine, provider: AIProvider, job: CompilationJob,
    model: str | None = None,
    *,
    compact: bool = False,
    on_progress: Callable[[str], None] | None = None,
    on_call: Callable[[RoleCall], None] | None = None,
) -> None:
    scope = ArtifactScope(brand_id=brand_id)
    try:
        with Session(engine) as db:
            store = ArtifactStore(db)
            previous = store.load(scope)
            version = previous.version if previous else 0
            documents = store.source_documents(scope)
            fingerprint = fingerprint_documents(documents)
            corpus = build_corpus(documents)
        if corpus.is_empty:
            raise ValueError("Add a source containing text before compiling.")
        def record(call: RoleCall) -> None:
            job.record(call)
            if on_call is not None:
                on_call(call)

        session = ModelSession(
            provider=provider,
            prompt_engine=get_prompt_engine(PROMPTS_DIR),
            events=EventBus(),
            model_router=ModelRouter(overrides=validate_overrides(
                {"knowledge_compiler": model} if model else None
            )),
            execution_id=f"knowledge:{brand_id}",
            on_call=record,
            effort="medium" if compact else None,
        )

        def progress(_stage: str, message: str) -> None:
            job.say(message)
            if on_progress is not None:
                on_progress(message)

        compiler = KnowledgeCompiler(session, compact=True) if compact else KnowledgeCompiler(session)
        artifacts = await compiler.compile(corpus, on_progress=progress)
        if compact:
            artifacts.notes.append("First-campaign knowledge covers selected pages and decision-relevant evidence. Compile sources to read them in more depth.")
        with Session(engine) as db:
            store = ArtifactStore(db)
            if db.get(Brand, brand_id) is None:
                raise ValueError("This brand was deleted during compilation.")
            if fingerprint_documents(store.source_documents(scope)) != fingerprint:
                raise ValueError("Sources changed during compilation. Please compile again.")
            latest = store.load(scope)
            if (latest.version if latest else 0) != version:
                raise ValueError("Knowledge changed during compilation. Please compile again.")
            saved = store.save(scope, artifacts, fingerprint)
        job.state = "completed"
        job.say(f"Knowledge compiled (v{saved.version}).")
    except asyncio.CancelledError:
        job.state = "failed"
        job.say("Compilation interrupted. Please retry.")
        raise
    except Exception as exc:
        logger.exception("Knowledge compilation failed for %s", brand_id)
        job.state = "failed"
        job.say(str(exc))
    finally:
        job.finished_at = datetime.now(UTC)


def all_jobs():
    from app.orchestration import background_jobs
    return list(background_jobs.latest("knowledge").values()) if background_jobs.enabled() else list(jobs.values())


def job_for(brand_id):
    from app.orchestration import background_jobs
    return background_jobs.latest("knowledge", brand_id).get(brand_id) if background_jobs.enabled() else jobs.get(brand_id)
