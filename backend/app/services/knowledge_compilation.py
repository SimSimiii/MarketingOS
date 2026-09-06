"""Standalone compilation jobs; the last successful artifact stays available."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import Engine
from sqlmodel import Session

from app.ai.base import AIProvider
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR
from app.knowledge.compiler import KnowledgeCompiler
from app.knowledge.store import ArtifactScope, ArtifactStore, build_corpus, fingerprint_documents
from app.models.brand import Brand
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession, RoleCall
from app.runtime.prompt_engine import get_prompt_engine

logger = logging.getLogger(__name__)


class CompilationStatus(BaseModel):
    state: Literal["idle", "running", "completed", "failed"] = "idle"
    message: str = ""


class CompilationJob(CompilationStatus):
    brand_id: UUID
    brand_name: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    log: list[str] = Field(default_factory=list)
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def say(self, message: str) -> None:
        self.message = message
        self.log.append(message)

    def record(self, call: RoleCall) -> None:
        self.calls += 1
        self.input_tokens += call.billable_input_tokens
        self.output_tokens += call.output_tokens
        self.log.append(
            f"Knowledge compiler · {call.model} · {call.duration_ms / 1000:.1f}s · "
            f"{call.billable_input_tokens:,} in / {call.output_tokens:,} out"
        )


# Like market jobs, these are process-local: a restart permits a fresh attempt.
jobs: dict[UUID, CompilationJob] = {}
tasks: set[asyncio.Task] = set()


def start_compilation(
    brand_id: UUID, engine: Engine, provider: AIProvider, brand_name: str,
) -> CompilationJob:
    current = jobs.get(brand_id)
    if current is not None and current.state == "running":
        return current
    job = CompilationJob(state="running", brand_id=brand_id, brand_name=brand_name)
    job.say("Reading knowledge sources…")
    jobs[brand_id] = job
    task = asyncio.create_task(_compile(brand_id, engine, provider, job))
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    return job


async def _compile(
    brand_id: UUID, engine: Engine, provider: AIProvider, job: CompilationJob,
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
        session = ModelSession(
            provider=provider,
            prompt_engine=get_prompt_engine(PROMPTS_DIR),
            events=EventBus(),
            model_router=ModelRouter(),
            execution_id=f"knowledge:{brand_id}",
            on_call=job.record,
        )

        def progress(_stage: str, message: str) -> None:
            job.say(message)

        artifacts = await KnowledgeCompiler(session).compile(corpus, on_progress=progress)
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
