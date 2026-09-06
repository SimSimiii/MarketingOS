import asyncio
import time
from threading import Event
from uuid import uuid4

from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.compiler import KnowledgeCompiler


def brand_with_sources(client):
    brand = client.post("/api/brands", json={"name": "Compiler test"}).json()["id"]
    response = client.post("/api/knowledge", json={
        "brand_id": brand, "content": "Our software writes release notes for developers.",
        "source_type": "text",
    })
    assert response.status_code == 201, response.text
    return brand


def wait_for_job(client, brand):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        job = client.get(f"/api/brands/{brand}/knowledge/compile").json()
        if job["state"] != "running":
            return job
        time.sleep(0.02)
    raise AssertionError("Compilation did not finish")


def test_compile_and_recompile_without_campaign(client):
    brand = brand_with_sources(client)
    for version in (1, 2):
        response = client.post(f"/api/brands/{brand}/knowledge/compile")
        assert response.status_code == 202
        assert wait_for_job(client, brand)["state"] == "completed"
        base = client.get("/api/knowledge/base", params={"brand_id": brand})
        assert base.status_code == 200
        assert base.json()["version"] == version
        jobs = client.get("/api/knowledge/jobs")
        assert jobs.status_code == 200
        job = next(job for job in jobs.json() if job["brand_id"] == brand)
        assert job["brand_name"] == "Compiler test"
        assert job["state"] == "completed"
        assert job["finished_at"] is not None
        assert job["calls"] >= 4
        assert any("Knowledge compiler" in line for line in job["log"])
        assert job["log"][-1] == f"Knowledge compiled (v{version})."


def test_failed_recompile_keeps_previous_artifacts(client, monkeypatch):
    brand = brand_with_sources(client)
    client.post(f"/api/brands/{brand}/knowledge/compile")
    assert wait_for_job(client, brand)["state"] == "completed"

    async def fail(*args, **kwargs):
        raise ValueError("Model unavailable")

    monkeypatch.setattr(KnowledgeCompiler, "compile", fail)
    client.post(f"/api/brands/{brand}/knowledge/compile")
    job = wait_for_job(client, brand)
    assert job == {"state": "failed", "message": "Model unavailable"}
    assert client.get(f"/api/brands/{brand}/knowledge").json()["version"] == 1
    listed = client.get("/api/knowledge/jobs").json()
    assert listed[0]["state"] == "failed"
    assert listed[0]["log"][-1] == "Model unavailable"
    assert listed[0]["finished_at"] is not None


def test_reject_empty_and_unknown_brand(client):
    brand = client.post("/api/brands", json={"name": "Empty"}).json()["id"]
    assert client.post(f"/api/brands/{brand}/knowledge/compile").status_code == 400
    assert client.post(f"/api/brands/{uuid4()}/knowledge/compile").status_code == 404


def test_build_corpus_deduplicates_legacy_sources():
    from app.knowledge.store import build_corpus
    from app.models.knowledge_document import KnowledgeDocument

    first = KnowledgeDocument(title="First", content="Some unique source text", source_type="text")
    duplicate = KnowledgeDocument(title="Copy", content=first.content, source_type="text")
    corpus = build_corpus([first, duplicate])
    assert len(corpus.documents) == 1
    assert corpus.documents[0].id == str(first.id)


def test_duplicate_start_and_sources_changed_during_compile(client, monkeypatch):
    release = Event()
    calls = []

    async def slow_compile(*args, **kwargs):
        calls.append(1)
        while not release.is_set():
            await asyncio.sleep(0.01)
        return KnowledgeArtifacts()

    monkeypatch.setattr(KnowledgeCompiler, "compile", slow_compile)
    brand = brand_with_sources(client)
    try:
        for _ in range(2):
            assert client.post(f"/api/brands/{brand}/knowledge/compile").status_code == 202
        jobs = client.get("/api/knowledge/jobs").json()
        assert len(jobs) == 1
        assert jobs[0]["brand_id"] == brand
        assert jobs[0]["state"] == "running"
        assert jobs[0]["finished_at"] is None
        assert jobs[0]["message"] == "Reading knowledge sources…"
        response = client.post("/api/knowledge", json={
            "brand_id": brand, "content": "A newly attached document with additional facts.",
        })
        assert response.status_code == 201
    finally:
        release.set()
    job = wait_for_job(client, brand)
    assert calls == [1]
    assert job["state"] == "failed"
    assert "Sources changed" in job["message"]
    assert client.get(f"/api/brands/{brand}/knowledge").status_code == 404


def test_live_compilations_exclude_deleted_brands(client):
    brand = brand_with_sources(client)
    client.post(f"/api/brands/{brand}/knowledge/compile")
    assert wait_for_job(client, brand)["state"] == "completed"
    assert client.delete(f"/api/brands/{brand}").status_code == 204
    assert client.get("/api/knowledge/jobs").json() == []
