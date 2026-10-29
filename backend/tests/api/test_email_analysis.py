"""Synthetic drafts: a documented function and a made-up result are different checks."""
import json
import time
from uuid import UUID, uuid4

from sqlmodel import Session

from app.knowledge.artifacts import BusinessProfile, KnowledgeArtifacts
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger
from app.models.email_analysis import EmailAnalysis
from app.models.knowledge_artifacts import KnowledgeArtifactSet
from app.services.email_analysis_service import reap_email_analyses


def brand(client):
    return client.post("/api/brands", json={"name": "Synthetic repair software"}).json()["id"]


def knowledge(engine, brand_id):
    with Session(engine) as db:
        db.add(KnowledgeArtifactSet(brand_id=UUID(brand_id), payload=KnowledgeArtifacts(
            business=BusinessProfile(company_name="RepairDesk", what_it_does="repair tracking software"),
            evidence=EvidenceLedger(entries=[Evidence(
                id="E1", kind=EvidenceKind.FEATURE, claim="Track repair status",
                verbatim="Track repair status in one shared view.", source="product documentation",
            )]),
        ).model_dump(mode="json")))
        db.commit()


def test_functional_draft_needs_no_testimonial_or_model_call(client, provider, engine):
    brand_id = brand(client)
    knowledge(engine, brand_id)
    response = client.post(f"/api/market/{brand_id}/email-analyses", json={
        "subject": "A shared repair view", "body": "RepairDesk is repair tracking software. Track repair status in one shared view. Reply to request a demonstration.",
        "audience": "Repair shop owners", "objective": "Request a demonstration",
    })
    assert response.status_code == 202, response.text
    row = response.json()
    assert row["state"] == "completed"
    assert row["calls"] == row["result"]["forecast_calls"] == 0
    assert not provider.requests
    assert not any(item["check"] == "evidence" for item in row["result"]["findings"])
    assert not any("testimonial" in item["detail"].lower() for item in row["result"]["findings"])


def test_absent_evidence_is_unverified_never_declared_false(client, engine):
    brand_id = brand(client)
    knowledge(engine, brand_id)
    row = client.post(f"/api/market/{brand_id}/email-analyses", json={
        "subject": "Repair outcomes", "body": "RepairDesk reduces repair time by 47% for every customer.",
    }).json()
    findings = [item for item in row["result"]["findings"] if item["category"] == "verification"]
    assert findings
    assert all("does not mean false" in item["action"] for item in findings)
    assert row["result"]["knowledge_version"] == 1


def test_uncompiled_brand_does_not_claim_product_checks_passed(client, provider):
    row = client.post(f"/api/market/{brand(client)}/email-analyses", json={
        "subject": "Synthetic retail launch", "body": "Our new lamp lasts 500 hours.",
    }).json()
    assert row["result"]["knowledge_version"] is None
    assert any(item["check"] == "knowledge" for item in row["result"]["findings"])
    assert not provider.requests


def test_capabilities_explain_cold_read_availability_before_spending(client):
    brand_id = brand(client)
    response = client.get(f"/api/market/{brand_id}/email-analyses/capabilities")
    assert response.status_code == 200
    assert response.json()["expected_calls"] == 1
    assert response.json()["schema_attempts"] == 2
    assert client.get(f"/api/market/{uuid4()}/email-analyses/capabilities").status_code == 404


def test_one_cold_reader_is_blind_and_persists_actionable_feedback(client, engine, provider):
    brand_id = brand(client)
    knowledge(engine, brand_id)
    provider.set_default("blind_reader", json.dumps({
        "understood": True, "what_it_sells": "Repair tracking software", "biggest_doubt": "Is setup included?",
        "pull": 6, "fixes": ["Explain the next step."], "would_act": False,
    }))
    started = client.post(f"/api/market/{brand_id}/email-analyses", json={
        "subject": "See repair status", "body": "RepairDesk is repair tracking software. Reply for a demonstration.",
        "audience": "An independent repair shop owner", "objective": "OBJECTIVE MUST NOT REACH COLD READER",
        "cold_read": True,
    })
    assert started.status_code == 202, started.text
    row = started.json()
    for _ in range(200):
        row = client.get(f"/api/market/{brand_id}/email-analyses/{row['id']}").json()
        if row["state"] != "running":
            break
        time.sleep(0.01)
    assert row["state"] == "completed", row
    assert row["calls"] == row["result"]["forecast_calls"] == 1
    assert row["result"]["reader"]["biggest_doubt"] == "Is setup included?"
    request = provider.requests_for("blind_reader")[0]
    assert "OBJECTIVE MUST NOT REACH" not in request.system_prompt
    assert "independent repair shop owner" in request.system_prompt
    assert "Track repair status in one shared view." not in request.system_prompt
    assert not request.tools
    assert "clicks_in_100" not in row["result"]["reader"]


def test_history_and_detail_are_brand_scoped(client):
    first, second = brand(client), brand(client)
    row = client.post(f"/api/market/{first}/email-analyses", json={"subject": "Private draft", "body": "Synthetic body"}).json()
    assert client.get(f"/api/market/{second}/email-analyses/{row['id']}").status_code == 404
    assert client.get(f"/api/market/{second}/email-analyses").json() == []
    assert client.post(f"/api/market/{uuid4()}/email-analyses", json={"subject": "x", "body": "x"}).status_code == 404


def test_restart_keeps_saved_checks(engine, client):
    brand_id = brand(client)
    with Session(engine) as db:
        row = EmailAnalysis(brand_id=UUID(brand_id), active_key=brand_id, result={"findings": [{"detail": "Saved"}]})
        db.add(row)
        db.commit()
        row_id = row.id
    reap_email_analyses(engine)
    with Session(engine) as db:
        row = db.get(EmailAnalysis, row_id)
        assert row.state == "degraded" and row.active_key is None
        assert row.result["findings"][0]["detail"] == "Saved"
