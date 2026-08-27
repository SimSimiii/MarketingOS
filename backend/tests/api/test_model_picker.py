"""The per-agent model picker, end to end over HTTP.

The picker is only worth anything if what it stores is what the router later
reads, and if a choice that cannot work is refused at the dialog rather than
thirteen minutes into the run it breaks.
"""

from fastapi.testclient import TestClient

from app.ai.model_router import ModelRouter, ModelTier
from tests.api.conftest import create_campaign


def test_the_catalog_offers_both_vendors(client: TestClient):
    catalog = client.get("/api/models").json()

    vendors = {model["vendor"] for model in catalog["models"]}
    assert vendors == {"anthropic", "openai"}
    assert {agent["id"] for agent in catalog["agents"]} >= {"email_writer", "strategist"}
    assert catalog["wildcard"] == "*"


def test_the_catalog_says_what_an_unpinned_agent_would_use(client: TestClient):
    """Without this the UI shows every row as "unset", which is what makes
    people pin agents they never needed to pin."""
    catalog = client.get("/api/models").json()
    assert set(catalog["tier_defaults"]) == {"fast", "balanced", "deep"}


def test_a_campaign_can_be_created_with_a_mixed_vendor_run(client: TestClient):
    campaign = create_campaign(
        client,
        model_overrides={"email_writer": "gpt-5.6-sol", "conversion_critic": "opus"},
    )

    stored = client.get(f"/api/campaigns/{campaign['id']}").json()["model_overrides"]
    assert stored == {"email_writer": "gpt-5.6-sol", "conversion_critic": "opus"}

    # What the picker stored is what the router reads - the whole point.
    router = ModelRouter(stored)
    assert router.resolve("email_writer", ModelTier.DEEP) == "gpt-5.6-sol"
    assert router.resolve("conversion_critic", ModelTier.DEEP) == "opus"
    assert router.resolve("blind_reader", ModelTier.BALANCED) == "sonnet"


def test_pinning_a_web_reading_agent_to_gpt_is_refused_with_a_reason(client: TestClient):
    response = client.post(
        "/api/campaigns",
        json={
            "name": "Doomed",
            "request": "three emails",
            "product_description": "a thing",
            "model_overrides": {"rival_scout": "gpt-5.6-sol"},
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "Rival scout" in detail and "web_fetch" in detail


def test_a_typo_in_an_agent_name_is_refused_rather_than_ignored(client: TestClient):
    response = client.post(
        "/api/campaigns",
        json={
            "name": "Typo",
            "request": "three emails",
            "product_description": "a thing",
            "model_overrides": {"emial_writer": "opus"},
        },
    )

    assert response.status_code == 422
    assert "not an agent" in response.json()["detail"]


def test_the_picker_can_be_changed_after_the_campaign_exists(client: TestClient):
    campaign = create_campaign(client)

    client.put(
        f"/api/campaigns/{campaign['id']}/policy",
        json={"model_overrides": {"*": "gpt-5.6-sol"}},
    ).raise_for_status()

    assert client.get(f"/api/campaigns/{campaign['id']}").json()["model_overrides"] == {
        "*": "gpt-5.6-sol"
    }


def test_changing_the_preset_does_not_wipe_the_pinned_models(client: TestClient):
    """The two screens that change a preset do not both show the picker. If
    omitting the field cleared it, changing a preset from the campaign list
    would silently throw away a choice made elsewhere."""
    campaign = create_campaign(client, model_overrides={"email_writer": "gpt-5.6-sol"})

    client.put(
        f"/api/campaigns/{campaign['id']}/policy", json={"preset": "maximum"}
    ).raise_for_status()

    stored = client.get(f"/api/campaigns/{campaign['id']}").json()
    assert stored["policy"]["preset"] == "maximum"
    assert stored["model_overrides"] == {"email_writer": "gpt-5.6-sol"}


def test_an_empty_map_is_how_the_picker_clears_every_pin(client: TestClient):
    campaign = create_campaign(client, model_overrides={"email_writer": "gpt-5.6-sol"})

    client.put(
        f"/api/campaigns/{campaign['id']}/policy", json={"model_overrides": {}}
    ).raise_for_status()

    assert client.get(f"/api/campaigns/{campaign['id']}").json()["model_overrides"] is None
