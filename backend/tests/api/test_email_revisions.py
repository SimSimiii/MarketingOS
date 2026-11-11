"""Steering before a run and editing an email after it, over HTTP.

Scripted provider: these tests count writer calls and read what reached the
prompts. Nothing here spends quota.
"""

import time
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlmodel import Session

from app.models.generated_asset import GeneratedAsset
from app.services import revision_service
from tests.api.conftest import create_campaign, run_campaign
from tests.marketing.conftest import email_draft

_EDIT_BODY = (
    "Your release deserves a note a customer can read. Notewright turns commits into release "
    "notes, so your team starts with a draft rather than an empty document.\n\n"
    "Pick the branch you want to describe, then review the result. Keep the useful details "
    "and edit the wording that needs your team's judgment.\n\n"
    "Start with the update you are preparing and decide whether the draft fits. The trial "
    "lets you try that workflow before deciding to use it for later announcements."
)


@pytest.mark.parametrize("original_supported", [True, False])
def test_legacy_original_gets_its_own_review_before_restoration(client, provider, engine, original_supported):
    execution_id = run_campaign(client)
    asset = _first_email(client, execution_id)
    with Session(engine) as db:
        row = db.get(GeneratedAsset, UUID(asset["id"]))
        meta = dict(row.asset_metadata)
        meta.pop("semantic_review", None)
        row.asset_metadata = meta
        db.add(row)
        db.commit()
    if not original_supported:
        provider.review("The original contains an unsupported promise.")
    calls = provider.calls_by_role["claim_reviewer"]
    provider.push("email_writer", email_draft(subject="A reviewed shorter version", body=_EDIT_BODY))
    _ask(client, execution_id, asset["id"], "Shorter")
    proposal = _settle(client, execution_id, asset["id"])["revisions"][0]
    assert proposal["state"] == "proposed"
    assert provider.calls_by_role["claim_reviewer"] == calls + 2
    accepted = client.post(f"/api/executions/{execution_id}/assets/{asset['id']}/revisions/{proposal['id']}/accept")
    assert accepted.status_code == 200
    restored = client.post(f"/api/executions/{execution_id}/assets/{asset['id']}/restore-original")
    assert restored.status_code == (200 if original_supported else 409)
    assert provider.calls_by_role["claim_reviewer"] == calls + 2, "selection does not spend another model call"
    assert _first_email(client, execution_id)["content"] == (asset["content"] if original_supported else proposal["content"])


def _first_email(client, execution_id: str) -> dict:
    assets = client.get(f"/api/executions/{execution_id}/assets").json()
    return next(asset for asset in assets if asset["position"] == 1)


def _settle(client, execution_id: str, asset_id: str) -> dict:
    for _ in range(400):
        history = client.get(f"/api/executions/{execution_id}/assets/{asset_id}/revisions").json()
        if not any(row["state"] == "running" for row in history["revisions"]):
            return history
        time.sleep(0.01)
    raise AssertionError("the proposal never settled")


def _ask(client, execution_id: str, asset_id: str, instruction: str, base: str | None = None):
    return client.post(
        f"/api/executions/{execution_id}/assets/{asset_id}/revisions",
        json={"instruction": instruction, "base_revision_id": base},
    )


# ------------------------------------------------------------------ steering


def test_steering_is_optional_and_reports_what_it_can_offer(client):
    campaign = create_campaign(client)
    assert campaign["steering"] is None
    before = client.get(f"/api/campaigns/{campaign['id']}/steering").json()
    assert before["knowledge_ready"] is False and before["options"] == []

    saved = client.put(f"/api/campaigns/{campaign['id']}/steering", json={
        "instructions": [{"text": "Make it shorter"}, {"text": "More detailed", "scope": "email", "position": 9}],
    })
    assert saved.status_code == 200, saved.text
    messages = " ".join(item["message"] for item in saved.json()["conflicts"])
    assert "opposite" in messages and "email 9" in messages
    assert client.get(f"/api/campaigns/{campaign['id']}").json()["steering"]["instructions"]

    cleared = client.put(f"/api/campaigns/{campaign['id']}/steering", json={})
    assert cleared.status_code == 200
    assert client.get(f"/api/campaigns/{campaign['id']}").json()["steering"] is None


def test_steering_choices_ride_on_the_stored_brief(client, provider):
    execution_id = run_campaign(client, steering={
        "instructions": [{"text": "Open on the trial", "scope": "email", "position": 2}],
    })
    result = client.get(f"/api/executions/{execution_id}/result").json()
    emails = result["result"]["brief"]["emails"]
    assert emails[1]["steering"]["directions"] == ["Open on the trial"]
    assert emails[0]["steering"]["directions"] == []
    assert any("Open on the trial" in (r.system_prompt or "")
               for r in provider.requests_for("email_writer"))


def test_knowledge_is_ready_after_the_first_run(client):
    # These campaigns attach no material, so the compile has nothing to offer;
    # the catalogue itself is covered in tests/marketing/test_steering.py.
    execution_id = run_campaign(client)
    campaign_id = client.get(f"/api/executions/{execution_id}/status").json()["campaign_id"]
    check = client.get(f"/api/campaigns/{campaign_id}/steering").json()
    assert check["knowledge_ready"] is True


# ------------------------------------------------------------------ revisions


def test_a_proposal_is_checked_on_its_own_and_accepting_keeps_the_original(client, provider):
    execution_id = run_campaign(client)
    asset = _first_email(client, execution_id)
    writer_calls = len(provider.requests_for("email_writer"))
    reader_calls = len(provider.requests_for("blind_reader"))
    # A body the run never wrote: the cycling default can hand back the very
    # email being edited, which is now (correctly) reported as no change.
    provider.push("email_writer", email_draft(subject="Release notes, shorter", body=_EDIT_BODY))

    started = _ask(client, execution_id, asset["id"], "Make it shorter")
    assert started.status_code == 202, started.text
    history = _settle(client, execution_id, asset["id"])
    proposal = history["revisions"][0]
    assert proposal["state"] == "proposed", proposal
    assert proposal["checks"] is not None and proposal["attempts"] == 1
    # One writer pass, and no cold read was bought or borrowed.
    assert len(provider.requests_for("email_writer")) == writer_calls + 1
    assert len(provider.requests_for("blind_reader")) == reader_calls
    task = provider.requests_for("email_writer")[-1].messages[-1].content
    assert "Make it shorter" in task and "current version" in task
    source_prompt = provider.requests_for("claim_reviewer")[-1].system_prompt
    assert "Current local adjustment: Make it shorter" in source_prompt
    # Unchanged until the user decides.
    assert _first_email(client, execution_id)["content"] == asset["content"]

    accepted = client.post(
        f"/api/executions/{execution_id}/assets/{asset['id']}/revisions/{proposal['id']}/accept"
    )
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["selected_revision_id"] == proposal["id"]
    assert body["original_content"] == asset["content"]
    current = _first_email(client, execution_id)
    assert current["content"] == proposal["content"]
    assert current["asset_metadata"]["pull"] is None, "an unread edit carries no reader score"
    assert current["asset_metadata"]["original"]["content"] == asset["content"]

    restored = client.post(f"/api/executions/{execution_id}/assets/{asset['id']}/restore-original")
    assert restored.status_code == 200
    assert _first_email(client, execution_id)["content"] == asset["content"]
    assert restored.json()["selected_revision_id"] is None


def test_another_adjustment_builds_on_the_chosen_proposal(client, provider):
    execution_id = run_campaign(client)
    asset = _first_email(client, execution_id)
    _ask(client, execution_id, asset["id"], "Make it shorter")
    first = _settle(client, execution_id, asset["id"])["revisions"][0]

    again = _ask(client, execution_id, asset["id"], "More direct", base=first["id"])
    assert again.status_code == 202, again.text
    second = _settle(client, execution_id, asset["id"])["revisions"][1]
    assert second["base_revision_id"] == first["id"]
    task = provider.requests_for("email_writer")[-1].messages[-1].content
    assert "Earlier changes the user asked for" in task and "Make it shorter" in task
    assert "More direct" in task


def test_a_proposal_that_breaks_a_check_is_repaired_once_then_cannot_be_used(client, provider):
    execution_id = run_campaign(client)
    asset = _first_email(client, execution_id)
    unsupported = email_draft(body=(
        "Teams save $4,999 a year with Notewright, guaranteed.\n\n"
        "Every release note started as a changelog nobody read, and ended as a paragraph you\n"
        "rewrote twice before shipping it.\n\n"
        "Notewright turns commits you already pushed into that paragraph.\n"
        "You edit it or you send it.\n\n"
        "Most people ask whether it sounds like them. It reads your older notes first, so it does."
    ))
    provider.push("email_writer", unsupported, unsupported)
    provider.review("The claimed $4,999 annual saving is unsupported.")
    before = len(provider.requests_for("email_writer"))

    _ask(client, execution_id, asset["id"], "Add a stronger number")
    proposal = _settle(client, execution_id, asset["id"])["revisions"][0]
    assert proposal["state"] == "blocked", proposal
    assert proposal["attempts"] == 2
    assert len(provider.requests_for("email_writer")) == before + 2, "bounded: one repair"
    assert "failed automatic checks" in provider.requests_for("email_writer")[-1].messages[-1].content
    assert proposal["checks"]["issues"]

    refused = client.post(
        f"/api/executions/{execution_id}/assets/{asset['id']}/revisions/{proposal['id']}/accept"
    )
    assert refused.status_code == 409
    assert _first_email(client, execution_id)["content"] == asset["content"]
    declined = client.post(
        f"/api/executions/{execution_id}/assets/{asset['id']}/revisions/{proposal['id']}/reject"
    )
    assert declined.status_code == 200
    assert declined.json()["revisions"][0]["state"] == "rejected"


def test_a_pass_that_changes_nothing_says_so_and_cannot_be_accepted(client, provider):
    # Seen live: asked to add a figure the material does not hold, the writer
    # rightly returned the same email - which the page then offered to accept.
    execution_id = run_campaign(client)
    asset = _first_email(client, execution_id)
    same = email_draft(subject="One subject only this test uses", body=_EDIT_BODY)
    provider.push("email_writer", same, same)
    _ask(client, execution_id, asset["id"], "Shorter")
    first = _settle(client, execution_id, asset["id"])["revisions"][0]
    assert first["state"] == "proposed"

    _ask(client, execution_id, asset["id"], "Add that customers save 5 hours a week", base=first["id"])
    second = _settle(client, execution_id, asset["id"])["revisions"][1]
    assert second["state"] == "unchanged", second
    assert "No change was made" in second["error"]
    refused = client.post(
        f"/api/executions/{execution_id}/assets/{asset['id']}/revisions/{second['id']}/accept"
    )
    assert refused.status_code == 409


def test_an_asset_from_another_run_is_not_reachable(client):
    first = run_campaign(client)
    second = run_campaign(client)
    asset = _first_email(client, second)
    assert _ask(client, first, asset["id"], "Shorter").status_code == 404
    assert client.get(f"/api/executions/{first}/assets/{asset['id']}/revisions").status_code == 404


def test_blank_and_overlong_requests_are_refused(client):
    execution_id = run_campaign(client)
    asset = _first_email(client, execution_id)
    assert _ask(client, execution_id, asset["id"], "   ").status_code == 422
    assert _ask(client, execution_id, asset["id"], "x" * 501).status_code == 422


def test_credit_billing_explains_rather_than_spends(client, provider, monkeypatch):
    execution_id = run_campaign(client)
    asset = _first_email(client, execution_id)
    monkeypatch.setattr(revision_service, "get_settings",
                        lambda: SimpleNamespace(credit_billing_enabled=True))
    before = len(provider.requests)
    refused = _ask(client, execution_id, asset["id"], "Shorter")
    assert refused.status_code == 409
    assert len(provider.requests) == before


def test_a_restart_never_leaves_a_proposal_running(client, engine):
    from uuid import UUID

    from sqlmodel import Session

    from app.models.email_revision import EmailRevision

    execution_id = run_campaign(client)
    asset = _first_email(client, execution_id)
    with Session(engine) as db:
        row = EmailRevision(asset_id=UUID(asset["id"]), campaign_execution_id=UUID(execution_id),
                            instruction="Shorter", active_key=asset["id"])
        db.add(row)
        db.commit()
        row_id = row.id
    revision_service.reap_email_revisions(engine)
    with Session(engine) as db:
        reaped = db.get(EmailRevision, row_id)
        assert reaped.state == "failed" and reaped.active_key is None
