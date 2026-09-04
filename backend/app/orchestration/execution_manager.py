import asyncio
import logging
from uuid import UUID

from sqlalchemy import Engine
from sqlmodel import Session

from app.ai.base import AIProvider
from app.marketing.cancellation import CancellationToken
from app.models.campaign import Campaign
from app.models.campaign_execution import CampaignExecution
from app.models.enums import ExecutionStatus
from app.orchestration.campaign_orchestrator import CampaignOrchestrator
from app.orchestration.execution_registry import registry

logger = logging.getLogger("marketingos.orchestration")


def launch(
    campaign: Campaign,
    ai_provider: AIProvider,
    engine: Engine,
    *,
    recommendation_snapshot: dict | None = None,
    generated_despite_recommendation: bool = False,
) -> CampaignExecution:
    """Create the execution row synchronously (so the caller has an id to
    return immediately) and hand the actual multi-minute run off to a
    background task on its own database session.

    `engine` is the bind of the session the request actually used (see
    CampaignService), not a hardcoded global - a background task that
    silently opened its own connection to the "real" database would go
    looking for a campaign that, in tests (or any setup where the engine is
    injected), was never written there.

    The FastAPI-injected session the request used is closed the moment the
    response is sent - long before a campaign finishes - so the background
    task must never touch it. It opens a fresh one instead.
    """
    with Session(engine) as session:
        execution = CampaignOrchestrator(session, ai_provider).create_execution(
            campaign,
            recommendation_snapshot=recommendation_snapshot,
            generated_despite_recommendation=generated_despite_recommendation,
        )

    cancel_token = CancellationToken()
    task = asyncio.create_task(_run(execution.id, campaign.id, ai_provider, engine, cancel_token))
    registry.register(execution.id, campaign.id, task, cancel_token)
    return execution


async def _run(
    execution_id: UUID,
    campaign_id: UUID,
    ai_provider: AIProvider,
    engine: Engine,
    cancel_token: CancellationToken,
) -> None:
    with Session(engine) as session:
        campaign = session.get(Campaign, campaign_id)
        execution = session.get(CampaignExecution, execution_id)
        if campaign is None or execution is None:
            logger.error("execution_manager: campaign or execution vanished before run started")
            return
        orchestrator = CampaignOrchestrator(session, ai_provider)
        try:
            await orchestrator.execute(campaign, execution, cancel_token=cancel_token)
        except Exception:
            logger.exception("execution_manager: background campaign run crashed")
            execution.status = ExecutionStatus.FAILED
            execution.error_message = "The campaign run crashed unexpectedly. Check server logs."
            session.add(execution)
            session.commit()


def reap_orphaned_executions() -> int:
    """Mark executions left RUNNING by a previous process (crash, restart)
    as failed. Call once at startup, before anything can register a new
    task in `registry` - otherwise a run that is legitimately in flight in
    the new process could be reaped out from under itself.

    Always uses the real application engine (not an injected one) - this
    only ever runs from app.main's lifespan, once, against whatever database
    the process actually owns."""
    from datetime import UTC, datetime

    from sqlmodel import select

    from app.core.database import engine

    reaped = 0
    with Session(engine) as session:
        orphans = session.exec(
            select(CampaignExecution).where(CampaignExecution.status == ExecutionStatus.RUNNING)
        ).all()
        for execution in orphans:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = "Interrupted by a server restart."
            execution.completed_at = datetime.now(UTC)
            session.add(execution)
            reaped += 1
        if reaped:
            session.commit()
    return reaped
