from fastapi.testclient import TestClient


def test_intent_survives_create_duplicate_and_draft_edit(client: TestClient):
    intent = {"objective": "announcement", "reader_relationship": "subscriber",
              "announcement": "Our new workshop opens on 20 October.",
              "reason_now": "Registration is open.", "desired_action": "View the programme"}
    response = client.post("/api/campaigns", json={
        "name": "Workshop", "request": "Write exactly one announcement email", "intent": intent,
        "strategy_mode": "auto",
    })
    assert response.status_code == 201, response.text
    campaign = response.json()
    assert campaign["policy"]["strategy_mode"] == "auto"
    assert campaign["intent"]["announcement"] == intent["announcement"]
    clone = client.post(f"/api/campaigns/{campaign['id']}/duplicate")
    assert clone.status_code == 201, clone.text
    assert clone.json()["intent"] == campaign["intent"]
    assert clone.json()["policy"]["strategy_mode"] == "auto"
    updated = client.put(f"/api/campaigns/{campaign['id']}/brief", json={
        "name": "Workshop", "request": "Write exactly one activation email",
        "intent": {**intent, "objective": "activation"},
    })
    assert updated.status_code == 200, updated.text
    assert updated.json()["intent"]["objective"] == "activation"


def test_legacy_campaign_keeps_intent_unknown_and_invalid_objective_is_rejected(client: TestClient):
    payload = {"name": "Legacy", "request": "Write one email to non-buyers"}
    response = client.post("/api/campaigns", json=payload)
    assert response.status_code == 201
    assert response.json()["intent"] is None
    assert client.post("/api/campaigns", json={**payload, "intent": {"objective": "invent-an-objective"}}).status_code == 422
