"""A campaign whose deliverable is a LinkedIn message.

Same creation form, same knowledge, same Strategist as an email campaign - and
then one message instead of a sequence. What these tests pin down is the part
that is easy to get wrong twice: that the plan really reaches the draft, and
that a channel with no cold reader does not quietly report scores nobody gave.
"""

import json

from fastapi.testclient import TestClient

from tests.api.conftest import await_terminal_status, create_campaign

CHANNEL = {
    "recipient_name": "Alice",
    "recipient_url": "https://linkedin.com/in/alice",
    "confirmed_context": "She runs release notes for a team of nine.",
    "language": "English",
    "kind": "message",
}
DRAFT = "Hi Alice, how do you handle release notes for nine people today?"


def linkedin_campaign(client: TestClient, **overrides) -> dict:
    return create_campaign(
        client,
        name="Alice on LinkedIn",
        request="Write one LinkedIn message to Alice about our release notes tool",
        goals="Get a reply about how they write release notes",
        channel={**CHANNEL, **overrides},
    )


def test_a_campaign_delivers_one_linkedin_message(client: TestClient, provider):
    provider.set_default("linkedin_writer", json.dumps({"body": DRAFT}))
    campaign = linkedin_campaign(client)
    assert campaign["channel"]["recipient_name"] == "Alice"

    execution_id = client.post(f"/api/campaigns/{campaign['id']}/start").json()["id"]
    execution = await_terminal_status(client, execution_id)
    assert execution["status"] == "completed", execution.get("error_message")

    assets = client.get(f"/api/executions/{execution_id}/assets").json()
    assert len(assets) == 1
    asset = assets[0]
    assert asset["asset_type"] == "linkedin_message"
    #: Ready to paste into a message box: no subject line, no HTML.
    assert asset["content"] == DRAFT
    assert asset["content_html"] is None
    assert asset["asset_metadata"]["characters"] == len(DRAFT)
    assert asset["asset_metadata"]["limit"] == 700
    assert asset["asset_metadata"]["single_idea"]
    assert "Alice" in asset["title"]


def test_the_message_executes_the_strategist_s_plan(client: TestClient, provider):
    provider.set_default("linkedin_writer", json.dumps({"body": DRAFT}))
    campaign = linkedin_campaign(client)
    execution_id = client.post(f"/api/campaigns/{campaign['id']}/start").json()["id"]
    await_terminal_status(client, execution_id)

    assert len(provider.requests_for("strategist")) == 1
    written = provider.requests_for("linkedin_writer")[0]
    #: The brief reached the writer, and so did the recipient context the user
    #: confirmed - the two things that separate this from the standalone tool.
    assert "idea number 1" in written.system_prompt
    assert "release notes for a team of nine" in written.system_prompt
    #: Nothing in this channel touches the open web.
    assert not written.tools


def test_no_cold_reader_grades_a_channel_it_has_never_read(client: TestClient, provider):
    provider.set_default("linkedin_writer", json.dumps({"body": DRAFT}))
    campaign = linkedin_campaign(client)
    execution_id = client.post(f"/api/campaigns/{campaign['id']}/start").json()["id"]
    await_terminal_status(client, execution_id)

    assert not provider.requests_for("blind_reader")
    assert not provider.requests_for("conversion_critic")
    assert not provider.requests_for("preference_judge")
    assert not provider.requests_for("sequence_reviewer")

    report = client.get(f"/api/executions/{execution_id}/result").json()["result"]["report"]
    assert report["delivered"] == 1
    assert report["promised"] == 1
    assert report["contract_violations"] == []
    #: The pull column is a placeholder here, and says so rather than reading
    #: as a zero out of ten.
    assert report["reads_expected"] is False
    assert report["emails"][0]["read_reported"] is False


def test_a_connection_note_is_held_to_its_own_limit(client: TestClient, provider):
    provider.push("linkedin_writer", json.dumps({"body": "Hi Alice. " * 40}))
    provider.set_default("linkedin_writer", json.dumps({"body": "Hi Alice, how do you write release notes?"}))
    campaign = linkedin_campaign(client, kind="connection")
    execution_id = client.post(f"/api/campaigns/{campaign['id']}/start").json()["id"]
    execution = await_terminal_status(client, execution_id)

    assert execution["status"] == "completed", execution.get("error_message")
    asset = client.get(f"/api/executions/{execution_id}/assets").json()[0]
    assert asset["asset_metadata"]["limit"] == 200
    assert asset["asset_metadata"]["characters"] <= 200
    assert len(provider.requests_for("linkedin_writer")) == 2


def test_a_draft_that_never_passes_its_gates_ships_nothing(client: TestClient, provider):
    provider.set_default("linkedin_writer", json.dumps({"body": "We cut your release notes by 94%."}))
    campaign = linkedin_campaign(client)
    execution_id = client.post(f"/api/campaigns/{campaign['id']}/start").json()["id"]
    execution = await_terminal_status(client, execution_id)

    assert execution["status"] == "failed"
    assert client.get(f"/api/executions/{execution_id}/assets").json() == []
    #: Two turns and then a stop - the writer is handed its own failures once.
    assert len(provider.requests_for("linkedin_writer")) == 2


def test_the_forecast_knows_this_run_buys_no_panel(client: TestClient):
    email_campaign = create_campaign(client)
    message_campaign = linkedin_campaign(client)

    email = client.get(f"/api/campaigns/{email_campaign['id']}/forecast").json()
    message = client.get(f"/api/campaigns/{message_campaign['id']}/forecast").json()

    assert message["emails"] == 1
    assert message["high"] < email["high"]
    #: Knowledge, a Strategist call and the writer's own correction turn.
    assert message["high"] - message["compile_high"] == 4
    assert message["low"] - message["compile_low"] == 2
