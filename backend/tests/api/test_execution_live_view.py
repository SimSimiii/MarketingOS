"""What a user watching a campaign run actually gets.

The live view's promise is that you can see what each role is doing while it
does it, open any role's own log, and lose nothing by reloading the page.
These tests hold that promise to the HTTP surface: the run is driven to
completion, then read back the way a client reads it.
"""

from fastapi.testclient import TestClient

from tests.api.conftest import run_campaign


def test_every_step_of_the_run_is_readable_afterwards(client: TestClient):
    execution_id = run_campaign(client)

    response = client.get(f"/api/executions/{execution_id}/logs")
    assert response.status_code == 200, response.text
    events = [row["event_type"] for row in response.json()]

    # The story a user should be able to follow: the ask, what the system
    # knows, the plan, each role working, the cold reader's verdict, the end.
    assert events[0] == "execution_started"
    assert "knowledge_ready" in events
    assert "brief_ready" in events
    assert "agent_started" in events
    assert "agent_completed" in events
    assert "review" in events
    assert "email_ready" in events
    assert "campaign_report" in events
    assert events[-1] == "execution_finished"


def test_a_single_roles_log_can_be_opened_on_its_own(client: TestClient):
    execution_id = run_campaign(client)

    response = client.get(f"/api/executions/{execution_id}/logs?agent_id=email_writer")
    assert response.status_code == 200, response.text
    rows = response.json()

    assert rows, "the writer ran, so it must have its own lines"
    assert {row["agent_id"] for row in rows} == {"email_writer"}
    assert any(row["event_type"] == "agent_completed" for row in rows)


def test_the_cold_readers_verdict_is_its_own_lane(client: TestClient):
    """Pull is this architecture's conversion score, and it is per email."""
    execution_id = run_campaign(client)

    rows = client.get(f"/api/executions/{execution_id}/logs?agent_id=blind_reader").json()
    reviews = [row for row in rows if row["event_type"] == "review"]

    assert len(reviews) == 3, "one cold read per email"
    assert all("/10" in row["message"] for row in reviews)
    assert all(row["step"] is not None for row in reviews)


def test_the_long_silence_of_a_model_call_is_filled_with_progress(client: TestClient):
    """Between a role starting and finishing sits one blocking model call -
    most of a campaign's wall-clock time. It must not be silent."""
    execution_id = run_campaign(client)

    debug = client.get(f"/api/executions/{execution_id}/logs?include_debug=true").json()
    types = [row["event_type"] for row in debug]

    assert "model_call_started" in types
    assert "model_call_finished" in types

    # ...and that instrumentation stays out of the default read.
    default = client.get(f"/api/executions/{execution_id}/logs").json()
    assert not any(row["event_type"] == "model_call_started" for row in default)


def test_progress_events_inherit_the_step_they_happened_in(client: TestClient):
    """The model session has no idea which step it is serving, but the UI
    groups everything by step - so the step has to travel with the event."""
    execution_id = run_campaign(client)

    rows = client.get(f"/api/executions/{execution_id}/logs?include_debug=true").json()
    model_calls = [row for row in rows if row["event_type"] == "model_call_started"]

    assert model_calls
    assert all(row["step"] is not None for row in model_calls)
    assert all(row["agent_id"] for row in model_calls)

    # And wrapping up belongs to the run, not to the last step it ran.
    finished = next(row for row in rows if row["event_type"] == "execution_finished")
    assert finished["step"] is None


def test_the_timeline_replays_the_run_for_a_page_that_arrived_late(client: TestClient):
    execution_id = run_campaign(client)

    response = client.get(f"/api/executions/{execution_id}/timeline")
    assert response.status_code == 200, response.text
    timeline = response.json()

    assert timeline["is_running"] is False
    assert timeline["last_event_id"] > 0
    assert timeline["events"][0]["type"] == "execution_started"
    # The payloads are what the stream sent, not a second rendering of them.
    completed = next(
        e
        for e in timeline["events"]
        if e["type"] == "agent_completed" and e["agent_id"] == "email_writer"
    )
    assert completed["agent_name"] == "Email Writer"
    assert completed["input_tokens"] > 0
    assert "assets_produced" in completed


def test_a_finished_run_tells_a_connecting_client_it_is_over(client: TestClient):
    execution_id = run_campaign(client)

    with client.stream("GET", f"/api/executions/{execution_id}/stream") as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert '"type": "execution_finished"' in body
    assert '"status": "completed"' in body


def test_a_run_that_ended_while_the_page_was_loading_still_sends_what_it_owes(
    client: TestClient,
):
    """The page loads its timeline over HTTP, then connects to the stream from
    the position that gave it. A run can finish in between - the end of a run
    is dense, and it is a couple of hundred milliseconds - and the events in
    that gap are the ones that matter: the report, the emails, the finish line.

    Before this the stream saw a run that was no longer running, sent one
    synthetic `execution_finished` and closed, so the page sat under a finished
    badge showing a timeline that stopped mid-run, with nothing saying why and
    nothing but a reload to fix it.
    """
    execution_id = run_campaign(client)
    timeline = client.get(f"/api/executions/{execution_id}/timeline").json()
    assert timeline["events"], "the run happened"

    # Connect as a client that had read only the first few events.
    resumed_from = 3
    with client.stream(
        "GET", f"/api/executions/{execution_id}/stream?after_event_id={resumed_from}"
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert '"type": "execution_finished"' in body
    assert '"type": "campaign_report"' in body, "the report is in the gap it was skipping"
    assert '"type": "email_ready"' in body
    # Everything after the client's position, and nothing before it.
    ids = [int(line[len("id: ") :]) for line in body.splitlines() if line.startswith("id: ")]
    assert ids and min(ids) > resumed_from
    assert ids == sorted(ids), "replayed in the order they happened"


def test_logs_and_timeline_404_on_an_unknown_execution(client: TestClient):
    unknown = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/api/executions/{unknown}/logs").status_code == 404
    assert client.get(f"/api/executions/{unknown}/timeline").status_code == 404


def test_running_executions_are_listed_for_the_dashboard(client: TestClient):
    # Nothing in flight once the run is done - and the route is not shadowed
    # by /{execution_id}.
    run_campaign(client)

    response = client.get("/api/executions/running")

    assert response.status_code == 200, response.text
    assert response.json() == []
