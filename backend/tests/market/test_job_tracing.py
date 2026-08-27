"""What a market job reports about itself while it runs.

A market job spends real quota - the cartographer runs on the deep tier, and
the prospect reader runs once per company - and it does so in a background
task with no execution row, no timeline and no receipt. Before this the only
thing a user watching one could see was a sentence. These are the tests for
the other half: which agent ran, on what, for how long, and at what cost.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.ai.model_router import ModelTier
from app.runtime.model_session import RoleCall
from app.services import market_service
from app.services.market_service import JobStatus, all_jobs


def call(role: str = "audience_cartographer", **overrides) -> RoleCall:
    payload: dict = {
        "role": role,
        "model": "claude-opus-5",
        "tier": ModelTier.DEEP,
        "input_tokens": 8_000,
        "output_tokens": 1_200,
        "duration_ms": 12_400.0,
        "cache_read_input_tokens": 2_000,
        "cost_usd": 0.0612,
    }
    payload.update(overrides)
    return RoleCall(**payload)


def test_a_finished_call_is_counted_and_traced():
    status = JobStatus(kind="audience", brand_id=uuid4())

    status.record(call())

    assert status.calls == 1
    # Cached input counted in: it is what the quota paid for, and reporting
    # only the uncached remainder is what made campaign runs look ~40% cheaper
    # than they were.
    assert status.input_tokens == 10_000
    assert status.cache_read_tokens == 2_000
    assert status.cost_usd == 0.0612
    line = status.log[-1]
    # Named for a person, not for the router: "audience_cartographer" is an id.
    assert "Audience cartographer" in line
    assert "claude-opus-5" in line
    assert "12.4s" in line
    assert "$0.06" in line


def test_a_trace_line_never_replaces_the_progress_line():
    """The progress line is the stage the job is at, in the user's language.
    Overwriting it with bookkeeping replaces something meaningful."""
    status = JobStatus(kind="audience", brand_id=uuid4())
    status.say("Working out who would actually buy this")

    status.record(call())

    assert status.message == "Working out who would actually buy this"
    assert len(status.log) == 2


def test_a_role_the_catalog_does_not_know_still_traces():
    status = JobStatus(kind="scan", brand_id=uuid4())

    status.record(call(role="something_new"))

    assert "something_new" in status.log[-1]


def test_the_board_lists_running_jobs_before_finished_ones():
    market_service._jobs.clear()
    older = JobStatus(
        kind="scan",
        brand_id=uuid4(),
        state="done",
        started_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    newer_done = JobStatus(
        kind="proof",
        brand_id=uuid4(),
        state="done",
        started_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    live = JobStatus(
        kind="audience",
        brand_id=uuid4(),
        started_at=datetime.now(UTC) - timedelta(minutes=9),
    )
    for job in (older, newer_done, live):
        market_service._jobs[job.brand_id] = job

    try:
        listed = all_jobs()
    finally:
        market_service._jobs.clear()

    # Running first however old, then most recent first: the board answers
    # "what is happening", and only then "what just happened".
    assert [job.kind for job in listed] == ["audience", "proof", "scan"]
