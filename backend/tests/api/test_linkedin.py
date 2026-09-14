import json
import time
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlmodel import Session

from app.ai.base import ResearchTool
from app.knowledge.artifacts import BusinessProfile, KnowledgeArtifacts
from app.market.demand import AudienceSegment, DemandMap
from app.market.store import MarketStore
from app.models.knowledge_artifacts import KnowledgeArtifactSet
from app.models.linkedin import LinkedInRun
from app.schemas.linkedin import MessageRequest, SearchRequest, linkedin_url
from app.services.linkedin_service import reap_linkedin_runs


def brand(client):
    return client.post("/api/brands", json={"name": "Notes"}).json()["id"]


def await_run(client, brand_id, run_id):
    for _ in range(200):
        runs = client.get(f"/api/market/{brand_id}/linkedin/runs").json()
        row = next(item for item in runs if item["id"] == run_id)
        if row["state"] != "running":
            return row
        time.sleep(0.01)
    raise AssertionError("LinkedIn job did not finish")


def knowledge(engine, brand_id):
    with Session(engine) as db:
        db.add(KnowledgeArtifactSet(brand_id=UUID(brand_id), payload=KnowledgeArtifacts(
            business=BusinessProfile(company_name="Notes", what_it_does="A note-taking app"),
        ).model_dump(mode="json")))
        db.commit()


CRITERIA = {
    "roles": ["Head of talent"], "industries": ["Recruitment"], "geographies": ["France"],
    "profile_signals": ["hiring page mentions technical roles"],
    "corroboration": ["a changelog announcing the feature"],
    "rationale": "They own the process",
}


def test_criteria_requires_compiled_knowledge(client, provider):
    response = client.post(f"/api/market/{brand(client)}/linkedin/criteria", json={})
    assert response.status_code == 409
    assert not provider.requests


def test_criteria_read_the_chosen_audience_and_never_the_web(client, provider, engine):
    brand_id = brand(client)
    knowledge(engine, brand_id)
    with Session(engine) as db:
        MarketStore(db).save_map(UUID(brand_id), DemandMap(segments=[AudienceSegment(
            name="Independent repair shops", who="a three-person shop", buyer_role="owner",
            signals=["a warranty page with an email address"], where=["UK repair directory"],
        )]))
    provider.set_default("linkedin_targeting", json.dumps(CRITERIA))
    started = client.post(f"/api/market/{brand_id}/linkedin/criteria",
                          json={"segment_name": "independent repair shops", "hint": "France only"})
    assert started.status_code == 202, started.text
    row = await_run(client, brand_id, started.json()["id"])
    assert row["state"] == "completed", row
    assert row["result"]["roles"] == ["Head of talent"]
    #: Written by code, so the user is told where the proposal came from
    #: rather than being told by the model that proposed it.
    assert row["result"]["basis"] == "the audience map (Independent repair shops)"
    request = provider.requests_for("linkedin_targeting")[0]
    assert "a warranty page with an email address" in request.system_prompt
    assert "France only" in request.system_prompt
    assert not request.tools


def test_criteria_fall_back_to_the_knowledge_base_when_nothing_is_mapped(client, provider, engine):
    brand_id = brand(client)
    knowledge(engine, brand_id)
    provider.set_default("linkedin_targeting", json.dumps(CRITERIA))
    started = client.post(f"/api/market/{brand_id}/linkedin/criteria", json={"segment_name": "Nobody"})
    row = await_run(client, brand_id, started.json()["id"])
    assert row["state"] == "completed", row
    assert row["result"]["basis"] == "the compiled knowledge base"


def test_a_search_can_be_driven_by_criteria_alone(client, provider, monkeypatch):
    monkeypatch.setattr(provider, "available_tools", lambda model=None: {ResearchTool.WEB_SEARCH})
    provider.set_default("linkedin_research", json.dumps({"candidates": [{
        "name": "Alice", "url": "https://linkedin.com/in/alice", "source_url": "https://example.com",
        "excerpt": "Alice, head of talent",
    }], "note": ""}))
    brand_id = brand(client)
    started = client.post(f"/api/market/{brand_id}/linkedin/search", json={"criteria": CRITERIA})
    assert started.status_code == 202, started.text
    row = await_run(client, brand_id, started.json()["id"])
    assert row["state"] == "completed", row
    assert len(row["result"]["candidates"]) == 1
    #: The saved job says who it was looking for, not only what it found.
    assert row["result"]["criteria"]["roles"] == ["Head of talent"]
    assert "Head of talent" in provider.requests_for("linkedin_research")[0].system_prompt


def test_a_search_with_neither_query_nor_criteria_is_refused():
    with pytest.raises(ValidationError):
        SearchRequest(criteria={"rationale": "who knows"})


def test_corroboration_alone_cannot_drive_a_search():
    """It is evidence that lives off LinkedIn. A search told to look for a
    changelog and nothing else has nobody to look for."""
    with pytest.raises(ValidationError):
        SearchRequest(criteria={"corroboration": ["a public postmortem"], "exclusions": ["students"]})


def test_where_an_audience_gathers_never_becomes_a_targeting_criterion(client, provider, engine):
    """Forums and directories describe a different channel.

    Sent as profile criteria they came back as "posts on indiehackers.com" and
    "activity on GitHub issues", which sent a LinkedIn search hunting Show HN
    threads and returning nobody. The audience's own signals still go, labelled
    as the company-level evidence they are.
    """
    brand_id = brand(client)
    knowledge(engine, brand_id)
    with Session(engine) as db:
        MarketStore(db).save_map(UUID(brand_id), DemandMap(segments=[AudienceSegment(
            name="Small product teams", who="a five-person team", buyer_role="CTO",
            signals=["a changelog naming an AI assistant"],
            where=["Hacker News Show HN threads", "indiehackers.com"],
        )]))
    provider.set_default("linkedin_targeting", json.dumps(CRITERIA))
    started = client.post(f"/api/market/{brand_id}/linkedin/criteria",
                          json={"segment_name": "Small product teams"})
    await_run(client, brand_id, started.json()["id"])

    prompt = provider.requests_for("linkedin_targeting")[0].system_prompt
    assert "indiehackers.com" not in prompt
    assert "Show HN" not in prompt
    assert "a changelog naming an AI assistant" in prompt
    assert "not necessarily readable on a profile" in prompt


def test_the_search_is_told_corroboration_never_excludes_a_candidate(client, provider, monkeypatch):
    monkeypatch.setattr(provider, "available_tools", lambda model=None: {ResearchTool.WEB_SEARCH})
    provider.set_default("linkedin_research", json.dumps({"candidates": [], "note": "none"}))
    brand_id = brand(client)
    started = client.post(f"/api/market/{brand_id}/linkedin/search", json={"criteria": CRITERIA})
    await_run(client, brand_id, started.json()["id"])

    prompt = provider.requests_for("linkedin_research")[0].system_prompt
    #: The bar the search is held to, and the budget it is held to. Both are
    #: what a zero-candidate run cost the user last time.
    assert "never a condition for returning somebody" in prompt
    assert "absence never excludes a candidate" in prompt
    assert "at most three searches" in prompt


def test_a_proposal_saved_before_the_split_still_drives_a_search():
    """`signals` was one list, and it was held to as conditions. Reading it as
    profile criteria keeps a job the user already paid for usable."""
    request = SearchRequest(criteria={"signals": ["headline says founding engineer"]})
    assert request.criteria is not None
    assert request.criteria.profile_signals == ["headline says founding engineer"]
    assert "Visible on the profile" in request.criteria.render()


@pytest.mark.parametrize("url", [
    "https://linkedin.com.evil.example/in/alice", "javascript:alert(1)",
    "http://linkedin.com/in/alice", "https://linkedin.com/feed/",
    "https://linkedin.com/in/alice/posts", "https://user@linkedin.com/in/alice",
    "https://linkedin.com:444/in/alice",
])
def test_rejects_non_profile_urls(url):
    with pytest.raises(ValueError):
        linkedin_url(url)


def test_canonical_profile_url():
    assert linkedin_url("https://fr.linkedin.com/in/alice/?trk=x") == "https://www.linkedin.com/in/alice"


def test_message_input_rejects_blank_names():
    with pytest.raises(ValidationError):
        MessageRequest(recipient_name="  ", recipient_url="https://linkedin.com/in/alice", objective="Talk")


def test_search_persists_scoped_results(client, provider, monkeypatch):
    monkeypatch.setattr(provider, "available_tools", lambda model=None: {ResearchTool.WEB_SEARCH})
    candidate = {"name": "Alice", "url": "https://linkedin.com/in/alice", "headline": "Founder",
                 "reason": "Relevant role", "source_url": "https://linkedin.com/in/alice",
                 "excerpt": "Alice, founder"}
    provider.set_default("linkedin_research", json.dumps({"candidates": [candidate, candidate], "note": "Search snippet only"}))
    first, second = brand(client), brand(client)
    started = client.post(f"/api/market/{first}/linkedin/search", json={"query": "French founders"})
    assert started.status_code == 202, started.text
    row = await_run(client, first, started.json()["id"])
    assert row["state"] == "completed", row
    assert len(row["result"]["candidates"]) == 1
    assert row["calls"] == 1
    assert client.get(f"/api/market/{second}/linkedin/runs").json() == []
    assert provider.requests_for("linkedin_research")[0].tools == [ResearchTool.WEB_SEARCH]


def test_company_search_filters_people(client, provider, monkeypatch):
    monkeypatch.setattr(provider, "available_tools", lambda model=None: {ResearchTool.WEB_SEARCH})
    provider.set_default("linkedin_research", json.dumps({"candidates": [{
        "name": "Alice", "url": "https://linkedin.com/in/alice", "source_url": "https://example.com", "excerpt": "Alice",
    }]}))
    brand_id = brand(client)
    started = client.post(f"/api/market/{brand_id}/linkedin/search", json={"query": "Agencies", "target": "companies"})
    row = await_run(client, brand_id, started.json()["id"])
    assert row["result"]["candidates"] == []


def test_search_requires_provider_capability(client, provider, monkeypatch):
    monkeypatch.setattr(provider, "available_tools", lambda model=None: set())
    response = client.post(f"/api/market/{brand(client)}/linkedin/search", json={"query": "Founders"})
    assert response.status_code == 409
    assert not provider.requests


def test_message_requires_knowledge(client, provider):
    response = client.post(f"/api/market/{brand(client)}/linkedin/messages", json={
        "recipient_name": "Alice", "recipient_url": "https://linkedin.com/in/alice", "objective": "Talk about notes",
    })
    assert response.status_code == 409
    assert not provider.requests


def test_message_repairs_unsupported_claim_without_web(client, provider, engine):
    brand_id = brand(client)
    knowledge(engine, brand_id)
    provider.push("linkedin_writer", json.dumps({"body": "Our app saves 95% of your time."}))
    provider.set_default("linkedin_writer", json.dumps({"body": "Bonjour Alice, comment organisez-vous vos notes ?"}))
    started = client.post(f"/api/market/{brand_id}/linkedin/messages", json={
        "recipient_name": "Alice", "recipient_url": "https://linkedin.com/in/alice", "objective": "Save 95% of their time", "kind": "connection",
    })
    assert started.status_code == 202, started.text
    row = await_run(client, brand_id, started.json()["id"])
    assert row["state"] == "completed", row
    assert row["calls"] == 2
    assert row["result"]["characters"] <= 200
    assert all(not request.tools for request in provider.requests_for("linkedin_writer"))


def test_invalid_message_never_ships(client, provider, engine):
    brand_id = brand(client)
    knowledge(engine, brand_id)
    provider.set_default("linkedin_writer", json.dumps({"body": "Hello [Name], we save 99% of your time."}))
    started = client.post(f"/api/market/{brand_id}/linkedin/messages", json={
        "recipient_name": "Alice", "recipient_url": "https://linkedin.com/in/alice", "objective": "Talk about notes",
    })
    row = await_run(client, brand_id, started.json()["id"])
    assert row["state"] == "failed"
    assert row["calls"] == 2
    assert not row["result"].get("body")
    with Session(engine) as db:
        assert db.get(LinkedInRun, UUID(row["id"])).active_key is None


def test_duplicate_job_is_refused_and_restart_releases_lock(client, provider, engine, monkeypatch):
    monkeypatch.setattr(provider, "available_tools", lambda model=None: {ResearchTool.WEB_SEARCH})
    brand_id = brand(client)
    with Session(engine) as db:
        row = LinkedInRun(brand_id=UUID(brand_id), active_key=brand_id, kind="search")
        db.add(row)
        db.commit()
    response = client.post(f"/api/market/{brand_id}/linkedin/search", json={"query": "Founders"})
    assert response.status_code == 409
    assert not provider.requests
    assert reap_linkedin_runs(engine) == 1
    provider.set_default("linkedin_research", '{"candidates": []}')
    response = client.post(f"/api/market/{brand_id}/linkedin/search", json={"query": "Founders"})
    assert response.status_code == 202
    assert await_run(client, brand_id, response.json()["id"])["state"] == "completed"


def test_migration_round_trip(engine):
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect

    path = Path(__file__).parents[2] / "alembic/versions/e8c4f6a25d03_linkedin_runs.py"
    spec = importlib.util.spec_from_file_location("linkedin_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.begin() as connection:
        LinkedInRun.__table__.drop(connection)
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        migration.upgrade()  # Development create_all may already have created it.
        columns = {column["name"] for column in inspect(connection).get_columns("linkedinrun")}
        assert columns == set(LinkedInRun.model_fields)
        assert any(item["column_names"] == ["active_key"] for item in inspect(connection).get_unique_constraints("linkedinrun"))
        migration.downgrade()
        assert not inspect(connection).has_table("linkedinrun")
        migration.upgrade()
        assert inspect(connection).has_table("linkedinrun")


@pytest.mark.parametrize("payload", [{"query": "ok", "limit": 0}, {"query": "founders", "limit": 11}, {"query": "  "}, {"query": "founders", "target": "emails"}])
def test_search_rejects_invalid_input_before_spending(client, provider, payload):
    response = client.post(f"/api/market/{brand(client)}/linkedin/search", json=payload)
    assert response.status_code == 422
    assert not provider.requests


def test_overlong_connection_note_is_rewritten(client, provider, engine):
    brand_id = brand(client)
    knowledge(engine, brand_id)
    provider.push("linkedin_writer", json.dumps({"body": "Hello Alice. " * 25}))
    provider.set_default("linkedin_writer", json.dumps({"body": "Hello Alice, how do you organise your notes?"}))
    started = client.post(f"/api/market/{brand_id}/linkedin/messages", json={
        "recipient_name": "Alice", "recipient_url": "https://linkedin.com/in/alice", "objective": "Talk about notes", "kind": "connection",
    })
    row = await_run(client, brand_id, started.json()["id"])
    assert row["state"] == "completed"
    assert row["calls"] == 2
    assert row["result"]["characters"] <= 200
