"""Lambda entry points for the campaign state machine.

Three handlers, one per state, each a thin shell around
`app.orchestration.stepped_runner`:

    plan     → how many emails this campaign will be
    craft    → writes the next one; the state machine calls it once per email
    finish   → sequence pass, report, assets

The division is by *duration*, not by topic. A `balanced` campaign budgets
itself 1200 seconds and `maximum` 2400, both past Lambda's 900-second ceiling,
but one email is 10 to 35 model calls - roughly four minutes - which fits with
room to spare. So the unit of work is one email, and the loop lives in Step
Functions where there is no timeout to exceed.

Each handler takes and returns a small JSON object. Nothing of the run itself
travels between them: the brief, the accepted copy and the outcomes are in
`CampaignRunState`, and the artifacts, corpus and market maps are reloaded from
their own tables. That is what keeps the payload far below Step Functions'
256 KB limit no matter how long the emails get.

`lifespan="off"` has no equivalent here because there is no ASGI app - but the
same reasoning applies and is worth stating: these handlers must never run
`init_db()` or `reap_orphaned_executions()`. The first would race concurrent
containers through `CREATE TABLE`; the second would mark every RUNNING
execution failed, which for a state machine mid-loop means killing the very run
this invocation was called to advance.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any
from uuid import UUID

from sqlmodel import Session

from app.ai.factory import get_ai_provider
from app.core.database import engine
from app.orchestration import stepped_runner

logging.getLogger("marketingos").setLevel(os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("marketingos.step_handlers")


def _execution_id(event: dict[str, Any]) -> UUID:
    """The one field every state passes.

    Step Functions hands a state the previous state's output, so `craft`
    receives what `plan` returned and finds the id in the same place. A missing
    id is a wiring error in the state machine and should fail loudly rather
    than default to something.
    """
    raw = event.get("execution_id")
    if not raw:
        raise ValueError("The event carries no execution_id.")
    return UUID(str(raw))


def _run(step, event: dict[str, Any]) -> dict[str, Any]:
    """Run one async step in its own session and return its JSON result.

    A session per invocation rather than a module-level one: a Lambda
    container is reused across invocations, and a SQLAlchemy session held
    across them would serve a later request rows it read minutes earlier -
    including an execution's status, which is the field the state machine
    branches on.
    """
    execution_id = _execution_id(event)
    provider = get_ai_provider()
    with Session(engine) as session:
        result = asyncio.run(step(session, execution_id, provider))
    logger.info("%s → %s", step.__name__, result.detail)
    return result.as_dict()


def plan(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """Compile the knowledge, decide the campaign, write the brief down."""
    return _run(stepped_runner.plan, event)


def craft(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """Write the next email. Called once per email by the state machine.

    Idempotent on position: the cursor and the email advance in one commit, so
    a retry of a step that succeeded and then timed out reporting writes the
    *next* email rather than a second copy of the last one.
    """
    return _run(stepped_runner.craft, event)


def finish(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """Read the emails as one sequence, report, and persist the deliverables."""
    return _run(stepped_runner.finish, event)
