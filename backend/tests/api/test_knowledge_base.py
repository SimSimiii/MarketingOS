"""The knowledge base over HTTP: the page a user browses their own facts on."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.knowledge.artifacts import BusinessProfile, KnowledgeArtifacts, OfferSheet, Plan
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger, EvidenceStrength
from app.knowledge.store import ArtifactScope, ArtifactStore


def compile_for_brand(engine, brand_id: str) -> None:
    """Stand in for a campaign run, which is the only thing that normally
    writes artifacts. The endpoint reads them; how they got there is the
    pipeline's business."""
    artifacts = KnowledgeArtifacts(
        business=BusinessProfile(company_name="Notewright", what_it_does="drafts release notes"),
        offer=OfferSheet(plans=[Plan(name="Team", price="$29/month")]),
        evidence=EvidenceLedger(
            entries=[
                Evidence(
                    id="E1",
                    kind=EvidenceKind.TESTIMONIAL,
                    claim="Foldwork cut release notes from 40 minutes to 9 seconds",
                    verbatim='"It replaced a job nobody wanted," says Dana Ellis at Foldwork.',
                    strength=EvidenceStrength.STRONG,
                ),
                Evidence(
                    id="E2",
                    kind=EvidenceKind.FEATURE,
                    claim="Connects to GitHub and GitLab over the API",
                    verbatim="Notewright connects to GitHub and GitLab over the API.",
                ),
            ]
        ),
    )
    with Session(engine) as session:
        ArtifactStore(session).save(ArtifactScope(brand_id=UUID(brand_id)), artifacts, "fp")
        session.commit()


def make_brand(client: TestClient) -> dict:
    response = client.post("/api/brands", json={"name": "Notewright"})
    assert response.status_code == 201, response.text
    return response.json()


def test_the_base_is_returned_shelved_and_ranked(client: TestClient, engine):
    brand = make_brand(client)
    compile_for_brand(engine, brand["id"])

    response = client.get(f"/api/knowledge/base?brand_id={brand['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= 3
    assert body["citable_total"] == 2
    shelves = {shelf["category"]: shelf for shelf in body["shelves"]}
    assert {entry["id"] for entry in shelves["proof"]["entries"]} == {"E1"}
    assert {entry["id"] for entry in shelves["technical"]["entries"]} == {"E2"}
    assert shelves["commercial"]["count"] >= 1


def test_every_shelf_ships_even_when_it_is_empty(client: TestClient, engine):
    """An empty shelf is the useful part: it says which page to upload next."""
    brand = make_brand(client)
    compile_for_brand(engine, brand["id"])

    shelves = client.get(f"/api/knowledge/base?brand_id={brand['id']}").json()["shelves"]

    empty = [shelf for shelf in shelves if shelf["count"] == 0]
    assert empty
    assert all(shelf["when_empty"] and shelf["buyer_question"] for shelf in empty)


def test_base_resolves_ahead_of_the_document_route(client: TestClient, engine):
    """FastAPI matches in declaration order - "base" reaching /{document_id}
    first would 422 as a malformed UUID rather than resolving here."""
    brand = make_brand(client)
    compile_for_brand(engine, brand["id"])

    assert client.get(f"/api/knowledge/base?brand_id={brand['id']}").status_code == 200


def test_an_uncompiled_brand_says_so_rather_than_returning_an_empty_base(client: TestClient):
    brand = make_brand(client)

    response = client.get(f"/api/knowledge/base?brand_id={brand['id']}")

    assert response.status_code == 404
    assert "first campaign run" in response.json()["detail"]


def test_knowledge_belongs_to_one_business(client: TestClient):
    """Without a scope the artifact store would answer with whichever set was
    written last, which is somebody else's business."""
    assert client.get("/api/knowledge/base").status_code == 400
