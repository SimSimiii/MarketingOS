"""A finished worker is not evidence that its drafts passed review."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlmodel import Session

from app.models.campaign_execution import CampaignExecution
from app.models.enums import ExecutionStatus
from tests.api.conftest import create_campaign


@pytest.mark.parametrize("outcome,warning", [
    ("completed", False), ("degraded", True), ("budget_exhausted", True),
    ("cancelled", True), ("failed", True), (None, False),
])
def test_review_state_reaches_campaign_lists_and_execution_history(client, engine, outcome, warning):
    campaign = create_campaign(client)
    with Session(engine) as session:
        execution = CampaignExecution(
            campaign_id=UUID(campaign["id"]), status=ExecutionStatus.COMPLETED,
            result={"run_status": outcome} if outcome else None,
        )
        session.add(execution)
        session.commit()
    row = next(row for row in client.get("/api/campaigns").json() if row["id"] == campaign["id"])
    assert row["last_run_status"] == "completed"
    assert row["last_run_needs_review"] is warning
    history = client.get(f"/api/campaigns/{campaign['id']}/executions").json()
    assert history[0]["needs_review"] is warning


def test_newer_clean_run_clears_an_old_warning_and_does_not_leak_to_other_campaigns(client, engine):
    campaign = create_campaign(client)
    other = create_campaign(client)
    now = datetime.now(UTC)
    with Session(engine) as session:
        for offset, outcome in [(0, "degraded"), (1, "completed")]:
            session.add(CampaignExecution(
                campaign_id=UUID(campaign["id"]), status=ExecutionStatus.COMPLETED,
                created_at=now + timedelta(seconds=offset), result={"run_status": outcome},
            ))
        session.commit()
    rows = {row["id"]: row for row in client.get("/api/campaigns").json()}
    assert not rows[campaign["id"]]["last_run_needs_review"]
    assert not rows[other["id"]]["last_run_needs_review"]
    assert rows[other["id"]]["last_run_status"] is None


def test_legacy_completed_run_with_a_stop_reason_still_needs_review(client, engine):
    campaign = create_campaign(client)
    with Session(engine) as session:
        session.add(CampaignExecution(
            campaign_id=UUID(campaign["id"]), status=ExecutionStatus.COMPLETED,
            error_message="Stopped after preserving one draft.",
        ))
        session.commit()
    row = next(row for row in client.get("/api/campaigns").json() if row["id"] == campaign["id"])
    assert row["last_run_needs_review"]
