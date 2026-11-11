"""Brands over HTTP: one workspace per business, and never a shared one.

The market, the sources and the compiled knowledge of a brand belong to that
brand. These tests are the guarantee the UI relies on when it scopes a page to
one: two registered businesses must never see each other's competitors, proof
queue or alerts, and the list that ranks them must count each one separately.
"""

import asyncio
import json
import time
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger
from app.knowledge.store import ArtifactScope, ArtifactStore, fingerprint_documents
from app.models.market import ProofCandidateRow, RadarEventRow
from app.orchestration import background_jobs
from tests.api.test_knowledge_base import compile_for_brand


def make_brand(client: TestClient, name: str) -> dict:
    response = client.post("/api/brands", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def test_a_brand_is_readable_on_its_own(client: TestClient):
    brand = make_brand(client, "Notewright")

    response = client.get(f"/api/brands/{brand['id']}")

    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Notewright"


@pytest.mark.parametrize("distributed", [False, True])
def test_review_pasted_email_returns_anchored_findings_and_sources(client, engine, provider, monkeypatch, distributed):
    dispatched = []
    if distributed:
        monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "api")
        monkeypatch.setenv("BACKGROUND_FUNCTION_NAME", "background")
        monkeypatch.setattr(background_jobs, "lambda_client", lambda: SimpleNamespace(
            invoke=lambda **options: dispatched.append(UUID(json.loads(options["Payload"])["job_id"])),
        ))
    brand = make_brand(client, "Notewright")
    path = f"/api/brands/{brand['id']}/draft-review"
    assert client.post(path, json={"text": "We import CSV files."}).status_code == 409
    assert not provider.calls_by_role
    url = "https://notewright.example/docs"
    quote = "Notewright imports CSV files."
    with Session(engine) as session:
        ArtifactStore(session).save(
            ArtifactScope(brand_id=UUID(brand["id"])),
            KnowledgeArtifacts(evidence=EvidenceLedger(entries=[
                Evidence(id="E1", kind=EvidenceKind.FEATURE, claim=quote, verbatim=quote, source=url),
            ])),
            fingerprint_documents([]),
        )
        session.commit()
    unsupported = "All imports are free."
    provider.push("claim_reviewer", json.dumps({
        "verdict": "revise", "summary": "Clarify the import pricing.", "findings": [],
        "claims": [
            {"text": quote, "status": "supported", "explanation": "The guide confirms the import.",
             "citations": [{"source_id": "E1", "quote": quote}]},
            {"text": unsupported, "status": "uncertain", "explanation": "No pricing is documented.",
             "citations": [{"source_id": "E1", "quote": "Pricing starts at $0."}]},
        ],
    }))
    response = client.post(path, json={"text": f"Subject: CSV import\n\n{quote} {unsupported}"})
    assert response.status_code == 202, response.text
    job_id = response.json()["id"]
    if distributed:
        assert dispatched == [UUID(job_id)]
        assert not provider.calls_by_role
        asyncio.run(background_jobs.execute(engine, dispatched[0], provider, context=None))
        asyncio.run(background_jobs.execute(engine, dispatched[0], provider, context=None))
    for _ in range(100):
        job = client.get(f"{path}/{job_id}").json()
        if job["state"] != "running":
            break
        time.sleep(0.02)
    assert job["state"] == "completed", job
    assert client.get(path).json() == job
    body = job["result"]
    assert not body["approved"]
    assert body["decision"]["claims"][1]["text"] == unsupported
    assert body["decision"]["claims"][1]["citations"] == []
    assert any(issue["gate"] == "review-reference" for issue in body["issues"])
    assert body["sources"] == {"E1": url}
    assert dict(provider.calls_by_role) == {"claim_reviewer": 1}


def test_blank_workspace_and_campaign_names_are_rejected(client: TestClient):
    assert client.post("/api/brands", json={"name": "   "}).status_code == 422
    assert client.post("/api/campaigns", json={
        "name": " \n ", "request": "Write exactly 1 email.",
    }).status_code == 422
    assert client.post("/api/campaigns", json={
        "name": "Valid", "request": " " * 20,
    }).status_code == 422


def test_new_names_are_trimmed_at_the_api_boundary(client: TestClient):
    brand = make_brand(client, "  Notewright  ")
    assert brand["name"] == "Notewright"
    response = client.post("/api/campaigns", json={
        "name": "  Welcome  ", "request": "  Write exactly 1 email.  ",
        "brand_id": brand["id"],
    })
    assert response.status_code == 201, response.text
    assert response.json()["name"] == "Welcome"
    assert response.json()["request"] == "Write exactly 1 email."


def test_an_unknown_brand_is_a_404_rather_than_the_first_one(client: TestClient):
    make_brand(client, "Notewright")

    response = client.get("/api/brands/8e0e2d1a-0000-4000-8000-000000000000")

    assert response.status_code == 404


def test_the_overview_counts_each_brand_separately(client: TestClient, engine):
    first = make_brand(client, "Notewright")
    second = make_brand(client, "Foldwork")
    compile_for_brand(engine, first["id"])

    client.post(f"/api/market/{first['id']}/rivals", json={"name": "Releasely"})
    client.post(f"/api/market/{second['id']}/rivals", json={"name": "Shipnotes"})
    client.post(f"/api/market/{second['id']}/rivals", json={"name": "Changelogger"})

    with Session(engine) as session:
        session.add(
            ProofCandidateRow(brand_id=UUID(first["id"]), claim="Dana Ellis vouched for us")
        )
        session.add(
            RadarEventRow(
                brand_id=UUID(second["id"]),
                headline="Shipnotes now names a customer",
                severity="acts_on_copy",
            )
        )
        session.commit()

    overview = client.get("/api/brands/overview")
    assert overview.status_code == 200, overview.text
    by_name = {row["name"]: row for row in overview.json()}

    assert by_name["Notewright"]["rivals"] == 1
    assert by_name["Foldwork"]["rivals"] == 2
    assert by_name["Notewright"]["pending_proof"] == 1
    assert by_name["Foldwork"]["pending_proof"] == 0
    assert by_name["Foldwork"]["unseen_alerts"] == 1
    assert by_name["Notewright"]["unseen_alerts"] == 0
    # Only the compiled one reports a version; registering a brand compiles
    # nothing, which is what the empty state on its workspace says.
    assert by_name["Notewright"]["knowledge_version"] == 1
    assert by_name["Notewright"]["compiled_at"] is not None
    assert by_name["Foldwork"]["knowledge_version"] is None


def test_a_muted_competitor_is_not_counted_against_the_brand(client: TestClient):
    brand = make_brand(client, "Notewright")
    rival = client.post(f"/api/market/{brand['id']}/rivals", json={"name": "Releasely"}).json()

    client.patch(f"/api/market/{brand['id']}/rivals/{rival['id']}", json={"muted": True})

    overview = client.get("/api/brands/overview").json()
    assert overview[0]["rivals"] == 0


def test_sources_are_counted_per_brand_and_a_one_off_belongs_to_nobody(client: TestClient):
    brand = make_brand(client, "Notewright")
    campaign = client.post(
        "/api/campaigns",
        json={
            "name": "Launch",
            "request": "Write me 3 emails",
            "product_description": "A note-taking app",
        },
    ).json()

    client.post(
        "/api/knowledge",
        json={"brand_id": brand["id"], "content": "Notewright drafts release notes.", "title": "About"},
    )
    client.post(
        "/api/knowledge",
        json={
            "campaign_id": campaign["id"],
            "content": "One-off copy notes for this run only.",
            "title": "Brief",
        },
    )

    overview = client.get("/api/brands/overview").json()
    assert overview[0]["sources"] == 1


def test_reading_the_site_suggests_its_look_and_saves_nothing(client: TestClient, monkeypatch):
    """The appearance form fills itself from this; the owner decides."""
    from app.api.routes import brands

    home = (
        '<html><head><meta name="theme-color" content="rgb(250, 247, 240)">'
        '<script type="application/ld+json">'
        '{"@type": "Organization", "logo": "/images/logo.png"}</script></head><body></body></html>'
    )

    async def read_home_page(url: str) -> tuple[str, str]:
        return home, "https://www.papier.example/"

    monkeypatch.setattr(brands, "read_home_page", read_home_page)
    brand = client.post(
        "/api/brands", json={"name": "Papier", "website_url": "https://papier.example"}
    ).json()

    response = client.post(f"/api/brands/{brand['id']}/style/detect")

    assert response.status_code == 200, response.text
    found = response.json()
    assert found["logo_url"] == "https://www.papier.example/images/logo.png"
    assert found["primary_color"] is None
    assert any("too pale" in note for note in found["notes"])
    assert client.get(f"/api/brands/{brand['id']}").json()["logo_url"] is None


def test_a_brand_without_a_website_has_nothing_to_read(client: TestClient):
    brand = make_brand(client, "Offline Co")

    response = client.post(f"/api/brands/{brand['id']}/style/detect")

    assert response.status_code == 400
