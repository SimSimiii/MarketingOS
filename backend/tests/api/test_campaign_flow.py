"""End-to-end HTTP test of the one flow that matters: a user asks for three
emails and gets three emails they can paste into their email tool."""

from fastapi.testclient import TestClient

from tests.api.conftest import await_terminal_status, create_campaign


def test_user_asks_for_three_emails_and_gets_three_emails(client: TestClient):
    campaign = create_campaign(client, product_url="https://example.com")
    assert campaign["request"].startswith("Write me 3 emails")

    started = client.post(f"/api/campaigns/{campaign['id']}/start")
    assert started.status_code == 202, started.text
    assert started.json()["status"] == "running"

    execution = await_terminal_status(client, started.json()["id"])
    assert execution["status"] == "completed", execution.get("error_message")

    assets = client.get(f"/api/executions/{execution['id']}/assets").json()
    assert len(assets) == 3
    assert [asset["position"] for asset in assets] == [1, 2, 3]
    assert all(asset["asset_type"] == "email" for asset in assets)
    # Ready to paste: plain text with a subject line, not a JSON payload.
    assert assets[0]["content"].startswith("Subject: ")
    assert assets[0]["title"]
    # Each email is a distinct piece of copy, not the same one three times.
    assert len({asset["content"] for asset in assets}) == 3


def test_the_deliverables_carry_how_hard_they_were_won(client: TestClient):
    """A user deciding whether to trust a draft should be able to see what a
    cold reader thought of it and how many rewrites it took."""
    campaign = create_campaign(client)
    execution_id = client.post(f"/api/campaigns/{campaign['id']}/start").json()["id"]
    await_terminal_status(client, execution_id)

    asset = client.get(f"/api/executions/{execution_id}/assets").json()[0]
    assert asset["asset_metadata"]["pull"] >= 0
    assert "revisions" in asset["asset_metadata"]
    assert asset["asset_metadata"]["single_idea"]


def test_the_run_records_the_campaign_report(client: TestClient):
    campaign = create_campaign(client)
    execution_id = client.post(f"/api/campaigns/{campaign['id']}/start").json()["id"]
    await_terminal_status(client, execution_id)

    result = client.get(f"/api/executions/{execution_id}/result").json()
    report = result["result"]["report"]

    assert report["delivered"] == 3
    assert report["promised"] == 3
    assert report["contract_violations"] == []
    assert result["result"]["brief"]["reader"]


def test_campaign_requires_a_real_request(client: TestClient):
    response = client.post(
        "/api/campaigns",
        json={"name": "Launch", "request": "hi", "product_description": "An app"},
    )
    assert response.status_code == 422


def test_pasted_knowledge_is_scoped_to_the_campaign(client: TestClient):
    campaign = create_campaign(client)

    added = client.post(
        "/api/knowledge",
        json={
            "campaign_id": campaign["id"],
            "title": "Brand voice",
            "content": "# Voice\n\nWe write plainly and never use exclamation marks.",
        },
    )
    assert added.status_code == 201, added.text
    document = added.json()[0]
    assert document["campaign_id"] == campaign["id"]
    assert document["word_count"] > 0

    scoped = client.get(f"/api/knowledge?campaign_id={campaign['id']}").json()
    assert [d["id"] for d in scoped] == [document["id"]]


def test_timestamps_are_serialized_with_an_explicit_utc_offset(client: TestClient):
    """Naive timestamps reach the browser as "...T19:31:43" and `new Date()`
    reads that as LOCAL time - every displayed time silently off by the
    viewer's UTC offset. The marker is what stops that."""
    campaign = create_campaign(client)
    assert campaign["created_at"].endswith(("Z", "+00:00")), campaign["created_at"]

    started = client.post(f"/api/campaigns/{campaign['id']}/start").json()
    assert started["started_at"].endswith(("Z", "+00:00")), started["started_at"]
    await_terminal_status(client, started["id"])

    listed = client.get("/api/campaigns").json()[0]
    assert listed["last_run_at"].endswith(("Z", "+00:00")), listed["last_run_at"]


def test_listing_documents_omits_their_text(client: TestClient):
    """An ingested PDF or site can be hundreds of KB. Listing must stay
    metadata-only; the text is fetched one document at a time."""
    campaign = create_campaign(client)
    body = "# Voice\n\n" + ("we write plainly and never shout. " * 500)
    created = client.post(
        "/api/knowledge",
        json={"campaign_id": campaign["id"], "title": "Brand voice", "content": body},
    ).json()[0]

    listed = client.get("/api/knowledge").json()[0]
    assert "content" not in listed
    assert listed["word_count"] > 0

    # ...but it is still retrievable in full, by id.
    fetched = client.get(f"/api/knowledge/{created['id']}").json()
    assert "we write plainly" in fetched["content"]
