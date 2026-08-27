"""HTTP coverage for the campaign lifecycle and execution-control surfaces
(archive/delete/duplicate/policy/cancel/restart) that sit around the core
"ask for copy, get copy" flow already covered by test_campaign_flow.py."""

import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.ai.factory import get_ai_provider
from app.main import app
from app.models.agent_execution import AgentExecution
from app.models.campaign_execution import CampaignExecution
from app.models.execution_log import ExecutionLog
from app.models.generated_asset import GeneratedAsset
from app.models.knowledge_artifacts import KnowledgeArtifactSet
from app.models.knowledge_document import KnowledgeDocument
from tests.api.conftest import await_terminal_status, create_campaign
from tests.marketing.conftest import RoleScriptedProvider


def test_archived_campaigns_are_hidden_by_default_and_visible_on_request(client: TestClient):
    campaign = create_campaign(client)

    archived = client.post(f"/api/campaigns/{campaign['id']}/archive")
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"
    assert archived.json()["archived_at"] is not None

    assert campaign["id"] not in [c["id"] for c in client.get("/api/campaigns").json()]
    assert campaign["id"] in [
        c["id"] for c in client.get("/api/campaigns?include_archived=true").json()
    ]

    unarchived = client.post(f"/api/campaigns/{campaign['id']}/unarchive")
    assert unarchived.json()["status"] == "active"
    assert unarchived.json()["archived_at"] is None
    assert campaign["id"] in [c["id"] for c in client.get("/api/campaigns").json()]


def test_deleting_a_campaign_removes_it(client: TestClient):
    campaign = create_campaign(client)

    deleted = client.delete(f"/api/campaigns/{campaign['id']}")
    assert deleted.status_code == 204

    assert client.get(f"/api/campaigns/{campaign['id']}").status_code == 404
    assert campaign["id"] not in [c["id"] for c in client.get("/api/campaigns").json()]


class _SlowFirstCallProvider(RoleScriptedProvider):
    """A scripted provider resolves synchronously, so a background run can
    finish before the very next HTTP call even lands - too fast to prove
    anything about "while it's still running". Stalling the first call gives
    the test a real window in which the run is guaranteed still in flight."""

    async def generate(self, request):
        if not self.requests:
            await asyncio.sleep(0.3)
        return await super().generate(request)


def test_cannot_delete_a_campaign_with_a_run_in_progress(
    client: TestClient, provider: RoleScriptedProvider
):
    """A background run holds a session and writes rows as it goes - deleting
    the campaign out from under it would corrupt that state."""
    app.dependency_overrides[get_ai_provider] = lambda: _SlowFirstCallProvider(provider.defaults)

    campaign = create_campaign(client)
    started = client.post(f"/api/campaigns/{campaign['id']}/start")
    execution_id = started.json()["id"]
    try:
        response = client.delete(f"/api/campaigns/{campaign['id']}")
        assert response.status_code == 409
    finally:
        # Drain the background run so it doesn't leak into the next test.
        await_terminal_status(client, execution_id)


def test_duplicating_a_campaign_copies_knowledge_but_not_executions(client: TestClient):
    campaign = create_campaign(client)
    client.post(
        "/api/knowledge",
        json={
            "campaign_id": campaign["id"],
            "title": "Brand voice",
            "content": "# Voice\n\nWe write plainly.",
        },
    )
    started = client.post(f"/api/campaigns/{campaign['id']}/start")
    await_terminal_status(client, started.json()["id"])

    duplicate = client.post(f"/api/campaigns/{campaign['id']}/duplicate")
    assert duplicate.status_code == 201, duplicate.text
    clone = duplicate.json()

    assert clone["id"] != campaign["id"]
    assert clone["request"] == campaign["request"]
    assert clone["name"] != campaign["name"]

    clone_knowledge = client.get(f"/api/knowledge?campaign_id={clone['id']}").json()
    assert len(clone_knowledge) == 1
    assert clone_knowledge[0]["title"] == "Brand voice"

    assert client.get(f"/api/campaigns/{clone['id']}/executions").json() == []


def test_deleting_a_campaign_takes_its_runs_assets_logs_and_knowledge_with_it(
    client: TestClient, engine
):
    """The cascade is a bulk delete - prove nothing is orphaned, including the
    knowledge compiled for this campaign alone."""
    campaign = create_campaign(client)
    client.post(
        "/api/knowledge",
        json={"campaign_id": campaign["id"], "title": "Voice", "content": "# Voice\n\nPlain."},
    )
    started = client.post(f"/api/campaigns/{campaign['id']}/start")
    await_terminal_status(client, started.json()["id"])

    with Session(engine) as session:
        assert session.exec(select(GeneratedAsset)).all()  # there was something to cascade
        assert session.exec(select(ExecutionLog)).all()
        assert session.exec(select(KnowledgeArtifactSet)).all()

    assert client.delete(f"/api/campaigns/{campaign['id']}").status_code == 204

    with Session(engine) as session:
        assert session.exec(select(CampaignExecution)).all() == []
        assert session.exec(select(AgentExecution)).all() == []
        assert session.exec(select(GeneratedAsset)).all() == []
        assert session.exec(select(ExecutionLog)).all() == []
        assert session.exec(select(KnowledgeDocument)).all() == []
        assert session.exec(select(KnowledgeArtifactSet)).all() == []


def test_campaign_list_reports_the_status_of_the_latest_run(client: TestClient):
    campaign = create_campaign(client)
    assert client.get("/api/campaigns").json()[0]["last_run_status"] is None

    started = client.post(f"/api/campaigns/{campaign['id']}/start")
    await_terminal_status(client, started.json()["id"])

    listed = client.get("/api/campaigns").json()[0]
    assert listed["last_run_status"] == "completed"
    assert listed["last_run_at"] is not None


def test_cancel_unknown_execution_is_404(client: TestClient):
    response = client.post("/api/executions/00000000-0000-0000-0000-000000000000/cancel")
    assert response.status_code == 404


def test_cancel_an_already_finished_execution_is_409(client: TestClient):
    campaign = create_campaign(client)
    started = client.post(f"/api/campaigns/{campaign['id']}/start")
    execution = await_terminal_status(client, started.json()["id"])
    assert execution["status"] == "completed"

    response = client.post(f"/api/executions/{execution['id']}/cancel")
    assert response.status_code == 409


def test_restart_without_a_prior_run_is_404(client: TestClient):
    campaign = create_campaign(client)
    response = client.post(f"/api/campaigns/{campaign['id']}/restart")
    assert response.status_code == 404


def test_restart_after_a_completed_run_starts_a_new_one(client: TestClient):
    campaign = create_campaign(client)
    started = client.post(f"/api/campaigns/{campaign['id']}/start")
    first = await_terminal_status(client, started.json()["id"])
    assert first["status"] == "completed"

    restarted = client.post(f"/api/campaigns/{campaign['id']}/restart")
    assert restarted.status_code == 202, restarted.text
    assert restarted.json()["id"] != first["id"]
    second = await_terminal_status(client, restarted.json()["id"])
    assert second["status"] == "completed"

    executions = client.get(f"/api/campaigns/{campaign['id']}/executions").json()
    assert len(executions) == 2


def test_a_policy_preset_routes_roles_to_its_overridden_model(
    client: TestClient, provider: RoleScriptedProvider
):
    campaign = create_campaign(client)
    updated = client.put(f"/api/campaigns/{campaign['id']}/policy", json={"preset": "fast"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["policy"]["preset"] == "fast"

    started = client.post(f"/api/campaigns/{campaign['id']}/start")
    execution = await_terminal_status(client, started.json()["id"])
    assert execution["status"] == "completed", execution.get("error_message")

    # "fast" moves every role to sonnet - the writer's own call must have gone
    # out with that model, proving the preset reached the pipeline instead of
    # only being stored on the campaign row.
    assert provider.requests_for("email_writer")[0].model == "sonnet"
    # ...and it turns the critic off entirely.
    assert provider.calls_by_role["conversion_critic"] == 0


def test_campaign_requires_a_valid_policy_preset(client: TestClient):
    campaign = create_campaign(client)
    response = client.put(
        f"/api/campaigns/{campaign['id']}/policy", json={"preset": "ultra-max-turbo"}
    )
    assert response.status_code == 422

def test_a_campaign_says_what_it_will_cost_before_it_is_run(client: TestClient):
    """The estimate is free and instant - nothing here calls a model - and it
    is the only thing standing between a preset described as "most thorough
    review" and a bill."""
    campaign = create_campaign(client)

    response = client.get(f"/api/campaigns/{campaign['id']}/forecast")
    assert response.status_code == 200, response.text
    forecast = response.json()

    assert forecast["emails"] == 3 and forecast["count_is_explicit"] is True
    assert 0 < forecast["low"] <= forecast["high"]
    assert forecast["knowledge_reused"] is False
    assert forecast["observed_runs"] == 0, "no history yet, so no figure is offered"
    assert forecast["observed_cost_per_email"] == 0


def test_the_forecast_learns_what_runs_actually_cost(client: TestClient):
    """The money beside the call count is not a price list - it is what this
    user's own runs came to, which is why it appears only once there are
    some."""
    campaign = create_campaign(client)
    started = client.post(f"/api/campaigns/{campaign['id']}/start")
    await_terminal_status(client, started.json()["id"])

    forecast = client.get(f"/api/campaigns/{campaign['id']}/forecast").json()
    assert forecast["observed_runs"] >= 1
    # The material has been read once and has not changed, so the next run
    # reads none of it again - which is the single largest saving available
    # and was previously invisible until the receipt arrived.
    assert forecast["knowledge_reused"] is True
    assert forecast["compile_low"] == 0


def test_a_forecast_for_a_campaign_that_does_not_exist_is_a_404(client: TestClient):
    response = client.get(f"/api/campaigns/{uuid4()}/forecast")
    assert response.status_code == 404


# ------------------------------------------------------------ presentation


def test_the_email_tier_is_stored_where_the_renderer_reads_it(client: TestClient):
    """`_presentation` reads `policy["email_tier"]`, and until a form wrote
    that key every email the system had ever produced came out plain - the
    branded tier was unreachable rather than unwanted."""
    created = client.post(
        "/api/campaigns",
        json={
            "name": "Launch",
            "request": "Write exactly 1 email announcing the launch",
            "product_description": "A note-taking app",
            "email_tier": "branded",
            "cta_url": "https://acme.test/launch",
        },
    )

    assert created.status_code == 201, created.text
    body = created.json()
    assert body["policy"]["email_tier"] == "branded"
    assert body["cta_url"] == "https://acme.test/launch"


def test_changing_the_preset_does_not_reset_the_look(client: TestClient):
    """The policy dict is rebuilt rather than merged on update, so anything
    stored in it that the form does not carry has to be put back by hand."""
    campaign = client.post(
        "/api/campaigns",
        json={
            "name": "Launch",
            "request": "Write exactly 1 email announcing the launch",
            "product_description": "A note-taking app",
            "email_tier": "branded",
        },
    ).json()

    updated = client.put(
        f"/api/campaigns/{campaign['id']}/policy", json={"preset": "fast"}
    )

    assert updated.status_code == 200, updated.text
    assert updated.json()["policy"]["preset"] == "fast"
    assert updated.json()["policy"]["email_tier"] == "branded"


def test_a_campaign_that_asks_for_nothing_stays_plain(client: TestClient):
    campaign = client.post(
        "/api/campaigns",
        json={
            "name": "Cold",
            "request": "Write exactly 1 email to people who have never heard of us",
            "product_description": "A note-taking app",
        },
    ).json()

    assert (campaign["policy"] or {}).get("email_tier") is None
    assert campaign["cta_url"] is None
