"""What holds a market job while it runs.

A scan, a proof hunt, an audience map and a prospect search all hand minutes
of work to a background task and return a status the page then polls. The
event loop keeps only a weak reference to a task, so if nothing else holds one
it can be collected before it finishes - and the consequence here is not a
lost scan but a locked brand: `_require_idle` reads the status, the status
still says "running", and every later job for that brand is refused for the
life of the process.
"""

import asyncio
import inspect

import pytest

from app.services import market_service


@pytest.mark.asyncio
async def test_a_launched_job_is_held_until_it_finishes():
    started, release = asyncio.Event(), asyncio.Event()

    async def job() -> None:
        started.set()
        await release.wait()

    market_service._spawn(job())
    await started.wait()

    assert market_service._running, "nothing but the event loop is holding the task"

    release.set()
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert not market_service._running, "a finished job must not be held forever"


def test_every_launcher_goes_through_the_one_place_that_holds_the_task():
    """The launchers are written by copying each other, so the guard has
    to be the only door rather than a line in each of them."""
    source = inspect.getsource(market_service)

    assert source.count("asyncio.create_task(") == 1, (
        "create_task belongs in _spawn and nowhere else - a task nothing holds "
        "can be collected mid-run"
    )
    assert "asyncio.create_task(" in inspect.getsource(market_service._spawn)
    assert source.count("_spawn(") == 7, "one definition and six launchers"
