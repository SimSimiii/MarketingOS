"""Brands over HTTP: one workspace per business, and never a shared one.

The market, the sources and the compiled knowledge of a brand belong to that
brand. These tests are the guarantee the UI relies on when it scopes a page to
one: two registered businesses must never see each other's competitors, proof
queue or alerts, and the list that ranks them must count each one separately.
"""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.market import ProofCandidateRow, RadarEventRow
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
