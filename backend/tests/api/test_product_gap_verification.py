"""A blocked dossier can acquire verified official facts before any campaign."""

import hashlib
import json
from datetime import UTC, datetime

import pytest

import app.api.routes.market as market_routes
from app.ai.base import ResearchTool
from app.market.audience_research import FetchedSource, FetchResult, FixedURLFetcher, SourceTier
from tests.api.test_relevance import answer, await_market_job, prepare_inputs


@pytest.fixture(autouse=True)
def market_engine(engine, provider, monkeypatch):
    monkeypatch.setattr(market_routes, "engine", engine)
    monkeypatch.setattr(provider, "available_tools", lambda _model: [ResearchTool.WEB_SEARCH])


def prepare_partial(client, provider, engine):
    brand = client.post("/api/brands", json={"name": "Notewright", "website_url": "https://notewright.com"}).json()
    prepare_inputs(engine, brand["id"])
    proposal = json.loads(answer())
    proposal["defining_need_fit"] = {
        "status": "partial", "evidence_ids": ["E1"],
        "unverified_requirements": ["Whether the product exports reports to CSV is not established."],
        "caveat": "Export workflow remains unverified.", "why": "A documented export is still needed.",
    }
    provider.set_default("relevance_analyst", json.dumps(proposal))
    response = client.post(f"/api/market/{brand['id']}/audience/relevance", json={"segment": "Repair shops"})
    assert response.status_code == 202, response.text
    job = await_market_job(client, brand["id"])
    assert job["state"] == "done", job
    return brand


def test_gap_verification_needs_a_current_dossier_and_spends_nothing_without_it(client, provider, engine):
    brand = client.post("/api/brands", json={"name": "Notewright"}).json()
    prepare_inputs(engine, brand["id"])
    response = client.post(f"/api/market/{brand['id']}/audience/relevance", json={
        "segment": "Repair shops", "verify_product_gaps": True,
    })
    assert response.status_code == 409 and "current dossier" in response.text
    assert not provider.requests_for("material_researcher")


def test_verified_product_material_is_persisted_and_the_new_dossier_uses_it(client, provider, engine, monkeypatch):
    brand = prepare_partial(client, provider, engine)
    source_url = "https://notewright.com/guide"
    quote = "Notewright exports reports to CSV from its report screen."
    source = FetchedSource(requested_url=source_url, final_url=source_url, title="Official export guide",
                           tier=SourceTier.INTERPRETATION, fetched_at=datetime.now(UTC),
                           content=quote, content_hash=hashlib.sha256(quote.encode()).hexdigest())
    async def fetch(_self, candidates):
        assert [item.url for item in candidates] == [source_url]
        return FetchResult(sources=[source])
    monkeypatch.setattr(FixedURLFetcher, "fetch", fetch)
    provider.push("material_researcher", json.dumps({"sources": [{"url": source_url, "official_for": "Notewright"}]}))
    provider.push("material_researcher", json.dumps({"claims": [{
        "source_id": "S1", "kind": "feature", "claim": quote, "verbatim": quote,
        "context": {"subject": "Notewright", "source_kind": "official_documentation", "claim_scope": "capability"},
    }]}))
    updated = json.loads(answer())
    updated["defining_need_fit"] = {"status": "addressed", "evidence_ids": ["R1"], "why": "The report export is documented."}
    provider.set_default("relevance_analyst", json.dumps(updated))
    response = client.post(f"/api/market/{brand['id']}/audience/relevance/rebuild", json={
        "segment": "Repair shops", "model": "gpt-5.6-sol", "verify_product_gaps": True,
    })
    assert response.status_code == 202, response.text
    job = await_market_job(client, brand["id"])
    assert job["state"] == "done", job
    assert job["calls"] == 3
    knowledge = client.get(f"/api/brands/{brand['id']}/knowledge").json()
    assert knowledge["version"] == 2
    fact = next(entry for entry in knowledge["artifacts"]["evidence"]["entries"] if entry["id"] == "R1")
    assert fact["source"] == source_url and fact["verbatim"] == quote
    assert not fact["document_id"].startswith("auto:")
    current = client.get(f"/api/market/{brand['id']}/audience/relevance/status", params={"segment": "Repair shops"}).json()
    assert current["status"] == "current" and current["dossier"]["knowledge_version"] == 2
    dossier_request = provider.requests_for("relevance_analyst")[-1]
    assert quote in dossier_request.system_prompt and not dossier_request.tools
    assert all(request.model == "gpt-5.6-sol" for request in provider.requests_for("material_researcher"))
    assert not provider.requests_for("email_writer")


def test_no_official_fact_keeps_the_existing_dossier_and_knowledge(client, provider, engine):
    brand = prepare_partial(client, provider, engine)
    provider.push("material_researcher", json.dumps({"sources": []}))
    response = client.post(f"/api/market/{brand['id']}/audience/relevance", json={
        "segment": "Repair shops", "verify_product_gaps": True,
    })
    assert response.status_code == 202, response.text
    job = await_market_job(client, brand["id"])
    assert job["state"] == "done" and job["calls"] == 1
    assert client.get(f"/api/brands/{brand['id']}/knowledge").json()["version"] == 1
    assert len(provider.requests_for("relevance_analyst")) == 1
    assert not provider.requests_for("email_writer")
