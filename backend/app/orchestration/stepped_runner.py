"""Running one campaign across several processes instead of one.

`CampaignOrchestrator.execute` runs a campaign inside a single process that
holds the brief, the accepted emails and the outcomes in local variables for
as long as it takes. That is the right shape on a machine that owns its own
uptime, and it is the only shape that supports material recovery, cancellation
and the in-memory registry.

It is not a shape a Lambda can have. A `balanced` campaign gives itself 1200
seconds and `maximum` 2400; Lambda stops at 900, and no amount of memory
changes that. But the *per-email* budget is far smaller - balanced is 10 to 35
model calls for one email, which is roughly four minutes - so a run fits
comfortably if the unit of work is one email rather than one campaign.

This module is that decomposition. Three entry points, each safe to call in a
fresh process:

    plan(execution_id)               → how many emails there will be
    craft(execution_id)              → writes the next one, advances the cursor
    finish(execution_id)             → sequence pass, report, assets

Between them the only thing that travels is `CampaignRunState` in Postgres -
see that model for why the list of what it holds is so short. A state machine
driving these passes an execution id and nothing else, which is also how the
payload stays far below Step Functions' 256 KB limit.

**`craft` is idempotent on position.** It reads `next_position`, writes that
email, and advances the cursor in the same transaction. A step retried after a
timeout that had in fact succeeded sees the advanced cursor and writes the next
email rather than a duplicate of the last one.

What this deliberately does not support, and why:

  - **Material recovery.** `_phase_material_recovery` re-plans and re-crafts
    everything from an enlarged closed world. A step that can restart the
    state machine is not a step. A run that needs it belongs in one process.
  - **The LinkedIn channel.** One message, one call, no sequence - it already
    fits in a single invocation and gains nothing from being split.
  - **A second worker.** `next_position` is the only cursor, so two workers on
    one execution would race it. The state machine runs one step at a time by
    construction; nothing here adds a lock that would make concurrency safe.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from pydantic import TypeAdapter
from sqlmodel import Session, select

from app.ai.base import AIProvider
from app.marketing.briefs import CampaignBrief
from app.marketing.craft import EmailOutcome
from app.marketing.email_copy import Email
from app.marketing.pipeline import CampaignRunResult
from app.models.campaign import Campaign
from app.models.campaign_execution import CampaignExecution
from app.models.campaign_run_state import CampaignRunState

logger = logging.getLogger("marketingos.stepped")

#: Serialized through Pydantic rather than by hand. `EmailOutcome` is a
#: dataclass of dataclasses and Pydantic models; a hand-written encoder would
#: drift from it the first time somebody added a field, and the drift would
#: show up as a report missing a column rather than as an error.
_OUTCOMES = TypeAdapter(list[EmailOutcome])
_EMAILS = TypeAdapter(list[Email])


@dataclass
class StepResult:
    """What a step hands the state machine.

    Deliberately small and JSON-shaped: these fields cross a process boundary
    and land in a Step Functions execution history, where a large payload is
    both a limit and a cost.
    """

    execution_id: str
    #: The position the next craft step should write, 1-based.
    next_position: int
    total_positions: int
    #: False once every email is written - the state machine's loop condition.
    more: bool
    status: str = "running"
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "next_position": self.next_position,
            "total_positions": self.total_positions,
            "more": self.more,
            "status": self.status,
            "detail": self.detail,
        }


class SteppedRunError(RuntimeError):
    """The run cannot proceed and the state machine should stop."""


def _load(session: Session, execution_id: UUID) -> tuple[CampaignExecution, Campaign]:
    execution = session.get(CampaignExecution, execution_id)
    if execution is None:
        raise SteppedRunError(f"No such execution: {execution_id}")
    campaign = session.get(Campaign, execution.campaign_id)
    if campaign is None:
        raise SteppedRunError(f"Execution {execution_id} has no campaign")
    return execution, campaign


def _state(session: Session, execution_id: UUID) -> CampaignRunState:
    state = session.exec(
        select(CampaignRunState).where(CampaignRunState.execution_id == execution_id)
    ).first()
    if state is None:
        raise SteppedRunError(
            f"Execution {execution_id} has no run state - plan() has not run."
        )
    return state


def _save(session: Session, state: CampaignRunState) -> None:
    state.updated_at = datetime.now(UTC)
    session.add(state)
    session.commit()


@contextmanager
def _admitted(session: Session, campaign: Campaign, *, resume: bool):
    """Admit this step's model work, and count what it spends.

    Without this the steps would call models with no reservation at all:
    `ModelSession` reads `current_work` and simply skips the accounting when it
    is empty, so a stepped run would be free of quota - not refused, not
    logged, just uncounted.

    `resume` is what keeps the arithmetic honest across invocations. The user
    bought one campaign; the plan step charges it and every step after attaches
    to that same purchase, so a five-email run costs one run rather than seven.
    """
    from app.runtime.work_limits import Reservation, current_work

    permit = Reservation(session.get_bind(), campaign.owner_id, resume=resume)
    token = current_work.set(permit)
    try:
        yield permit
    finally:
        current_work.reset(token)
        permit.finish()


# ─────────────────────────────────────────────────────────────── the steps ──


async def plan(session: Session, execution_id: UUID, ai_provider: AIProvider) -> StepResult:
    """Compile what is known, decide the campaign, write the brief down.

    One Strategist call and, on a corpus that has not changed since the last
    run, no compilation call at all - `_phase_knowledge` reuses the stored
    artifacts by fingerprint.
    """
    from app.orchestration.campaign_orchestrator import build_stepped_pipeline

    execution, campaign = _load(session, execution_id)
    pipeline, request, _ = build_stepped_pipeline(session, campaign, execution, ai_provider)

    if request.channel is not None:
        raise SteppedRunError(
            "The LinkedIn channel is one call and one message; run it in a single "
            "process rather than a state machine."
        )

    result = CampaignRunResult(usage=pipeline.session_usage)
    contract = pipeline.read_contract(request)
    with _admitted(session, campaign, resume=False):
        _, brief = await pipeline.plan(request, contract, result)

    state = session.exec(
        select(CampaignRunState).where(CampaignRunState.execution_id == execution_id)
    ).first() or CampaignRunState(execution_id=execution_id)
    state.brief = brief.model_dump(mode="json")
    state.contract = contract.model_dump(mode="json")
    state.intelligence = (
        result.intelligence.model_dump(mode="json") if result.intelligence else None
    )
    state.accepted = []
    state.outcomes = []
    state.next_position = 1
    state.total_positions = len(brief.emails)
    _save(session, state)

    logger.info("stepped: planned %s email(s) for %s", len(brief.emails), execution_id)
    return StepResult(
        execution_id=str(execution_id),
        next_position=1,
        total_positions=len(brief.emails),
        more=bool(brief.emails),
        detail=f"Planned {len(brief.emails)} email(s)",
    )


async def craft(session: Session, execution_id: UUID, ai_provider: AIProvider) -> StepResult:
    """Write one email - the step the state machine calls N times."""
    from app.orchestration.campaign_orchestrator import build_stepped_pipeline

    execution, campaign = _load(session, execution_id)
    state = _state(session, execution_id)

    if state.next_position > state.total_positions:
        # Already finished. Reached by a retry of a step that succeeded and
        # then timed out reporting it; answering "no more" is correct and
        # writes nothing.
        return StepResult(
            execution_id=str(execution_id),
            next_position=state.next_position,
            total_positions=state.total_positions,
            more=False,
            detail="Already complete",
        )

    pipeline, request, _ = build_stepped_pipeline(session, campaign, execution, ai_provider)
    brief = CampaignBrief.model_validate(state.brief)
    result = CampaignRunResult(usage=pipeline.session_usage)
    result.outcomes = _OUTCOMES.validate_python(state.outcomes)

    context = await pipeline.rebuild_context(request, result)
    previous = _EMAILS.validate_python(state.accepted)
    position = state.next_position

    with _admitted(session, campaign, resume=True):
        outcome = await pipeline.craft_position(
            request=request,
            brief=brief,
            context=context,
            result=result,
            position=position,
            previous=previous,
        )
    if outcome is None:
        state.abort_reason = "stopped"
        _save(session, state)
        return StepResult(
            execution_id=str(execution_id),
            next_position=state.next_position,
            total_positions=state.total_positions,
            more=False,
            status="degraded",
            detail=f"Stopped before email {position}",
        )

    # Cursor and content advance together. Written in one commit so a crash
    # between them cannot leave an email recorded twice or lost.
    state.accepted = _EMAILS.dump_python([*previous, outcome.email], mode="json")
    state.outcomes = _OUTCOMES.dump_python([*result.outcomes, outcome], mode="json")
    state.next_position = position + 1
    _save(session, state)

    more = state.next_position <= state.total_positions
    logger.info("stepped: wrote email %s/%s for %s", position, state.total_positions, execution_id)
    return StepResult(
        execution_id=str(execution_id),
        next_position=state.next_position,
        total_positions=state.total_positions,
        more=more,
        detail=f'Email {position} ready: "{outcome.email.subject}"',
    )


async def finish(session: Session, execution_id: UUID, ai_provider: AIProvider) -> StepResult:
    """Read the emails as one sequence, build the report, persist the assets."""
    from app.orchestration.campaign_orchestrator import (
        build_stepped_pipeline,
        persist_stepped_result,
        rehydrate_writer_rows,
    )

    execution, campaign = _load(session, execution_id)
    state = _state(session, execution_id)

    pipeline, request, observer = build_stepped_pipeline(session, campaign, execution, ai_provider)
    brief = CampaignBrief.model_validate(state.brief)
    contract = pipeline.read_contract(request)
    result = CampaignRunResult(usage=pipeline.session_usage)
    result.brief = brief
    result.outcomes = _OUTCOMES.validate_python(state.outcomes)
    result.abort_reason = state.abort_reason

    context = await pipeline.rebuild_context(request, result)
    result.artifacts = context.artifacts
    with _admitted(session, campaign, resume=True):
        await pipeline.conclude(
            request=request, contract=contract, brief=brief, context=context, result=result
        )

    # The writer rows were created by the craft steps, in processes this one
    # never shared. Without rebuilding the index every asset would be
    # orphaned and the run would hand over nothing.
    rehydrate_writer_rows(session, execution, observer)
    persist_stepped_result(session, campaign, execution, result, observer, ai_provider)
    logger.info("stepped: finished %s as %s", execution_id, result.status)
    return StepResult(
        execution_id=str(execution_id),
        next_position=state.next_position,
        total_positions=state.total_positions,
        more=False,
        status=result.status,
        detail=f"{result.deliverables} deliverable(s)",
    )


def elapsed_budget(started: float, policy_seconds: int | None) -> float | None:
    """How long a step may still run, in seconds.

    A step inherits the campaign's total budget, not a fresh one: five emails
    that each took the full campaign deadline would be a run that never ends.
    """
    if policy_seconds is None:
        return None
    return max(0.0, policy_seconds - (time.monotonic() - started))
