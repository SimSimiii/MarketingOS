"""The asynchronous Lambda path never leaves work on the HTTP process."""
from unittest.mock import Mock

import pytest
from sqlmodel import select

from app.models.background_job import BackgroundJob
from app.models.brand import Brand
from app.orchestration import background_jobs as jobs
from app.runtime.work_limits import WorkLimitError
from app.services import knowledge_compilation as knowledge
from tests.marketing.test_stepped_runner import provider, session  # noqa: F401


@pytest.fixture
def queued(session, provider, monkeypatch):  # noqa: F811
    monkeypatch.setenv("BACKGROUND_FUNCTION_NAME", "background-test")
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "api-test")
    monkeypatch.delenv("JOB_HOST", raising=False)
    client = Mock()
    monkeypatch.setattr(jobs, "lambda_client", lambda: client)
    brand = Brand(name="Empty test brand")
    session.add(brand)
    session.commit()
    status = knowledge.start_compilation(brand.id, session.get_bind(), provider, brand.name)
    row = session.exec(select(BackgroundJob)).one()
    return brand, status, row, client


def test_http_dispatch_is_persisted_and_duplicate_is_refused(session, provider, queued):  # noqa: F811
    brand, status, row, client = queued
    assert status.state == "running"
    assert jobs.decode(row).brand_id == brand.id
    assert client.invoke.call_args.kwargs["InvocationType"] == "Event"
    with pytest.raises(WorkLimitError):
        knowledge.start_compilation(brand.id, session.get_bind(), provider, brand.name)
    assert client.invoke.call_count == 1


@pytest.mark.asyncio
async def test_worker_persists_failure_without_sources_and_ignores_redelivery(session, provider, queued, monkeypatch):  # noqa: F811
    _, _, row, _ = queued
    monkeypatch.setenv("JOB_HOST", "true")
    await jobs.execute(session.get_bind(), row.id, provider, None)
    session.refresh(row)
    assert not row.active
    assert row.claimed
    assert row.status["state"] == "failed"
    assert "source" in row.status["message"]
    assert row.model_calls == 0
    before = dict(row.status)
    await jobs.execute(session.get_bind(), row.id, provider, None)
    session.refresh(row)
    assert row.status == before


def test_failure_destination_is_idempotent_and_blocks_future_calls(session, queued):  # noqa: F811
    _, _, row, _ = queued
    jobs.fail(session.get_bind(), row.id)
    jobs.fail(session.get_bind(), row.id)
    session.refresh(row)
    assert not row.active
    assert row.status["state"] == "failed"
    with pytest.raises(WorkLimitError):
        jobs.Permit(session.get_bind(), row.id, None).attempt()


@pytest.mark.asyncio
async def test_linkedin_dispatch_uses_persisted_run_and_claim(session, provider, queued, monkeypatch):  # noqa: F811
    from unittest.mock import AsyncMock

    from app.ai.base import ResearchTool
    from app.models.linkedin import LinkedInRun
    from app.schemas.linkedin import SearchRequest
    from app.services import linkedin_service as linkedin
    brand, _, initial, _client = queued
    jobs.fail(session.get_bind(), initial.id)
    monkeypatch.setattr(provider, "available_tools", lambda: {ResearchTool.WEB_SEARCH})
    work = AsyncMock(return_value={"candidates": []})
    monkeypatch.setattr(linkedin, "_work", work)
    run = linkedin.launch(session, brand.id, provider, SearchRequest(query="test engineers"))
    row = session.exec(select(BackgroundJob).where(BackgroundJob.category == "linkedin")).one()
    assert row.payload["run_id"] == str(run.id)
    monkeypatch.setenv("JOB_HOST", "true")
    await jobs.execute(session.get_bind(), row.id, provider, None)
    await jobs.execute(session.get_bind(), row.id, provider, None)
    session.expire_all()
    assert session.get(LinkedInRun, run.id).state == "completed"
    assert not session.get(BackgroundJob, row.id).active
    assert work.await_count == 1


@pytest.mark.asyncio
async def test_email_checks_are_saved_before_worker_and_failure_preserves_them(session, provider, queued, monkeypatch):  # noqa: F811
    from app.models.email_analysis import EmailAnalysis
    from app.schemas.email_analysis import EmailAnalysisRequest
    from app.services import email_analysis_service as analysis

    brand, _, initial, client = queued
    jobs.fail(session.get_bind(), initial.id)
    run = analysis.launch(session, brand.id, provider, EmailAnalysisRequest(
        subject="Synthetic lamp announcement", body="A lamp with adjustable brightness.", cold_read=True,
    ))
    row = session.exec(select(BackgroundJob).where(BackgroundJob.category == "email_analysis")).one()
    assert row.payload["run_id"] == str(run.id)
    assert run.result["findings"]  # missing knowledge/context already available
    assert run.calls == 0
    assert client.invoke.call_args.kwargs["InvocationType"] == "Event"
    saved = dict(run.result)
    jobs.fail(session.get_bind(), row.id)
    session.expire_all()
    interrupted = session.get(EmailAnalysis, run.id)
    assert interrupted.state == "degraded"
    assert interrupted.active_key is None
    assert interrupted.result == saved
    with pytest.raises(WorkLimitError):
        jobs.Permit(session.get_bind(), row.id, None).attempt()


@pytest.mark.asyncio
async def test_email_worker_runs_one_reader_and_ignores_duplicate_delivery(session, provider, queued, monkeypatch):  # noqa: F811
    from unittest.mock import AsyncMock

    from app.marketing.reader import BlindRead, PanelRead
    from app.models.email_analysis import EmailAnalysis
    from app.schemas.email_analysis import EmailAnalysisRequest
    from app.services import email_analysis_service as analysis

    brand, _, initial, _ = queued
    jobs.fail(session.get_bind(), initial.id)
    run = analysis.launch(session, brand.id, provider, EmailAnalysisRequest(
        subject="Synthetic course", body="A beginner course in bicycle repairs.", cold_read=True,
    ))
    row = session.exec(select(BackgroundJob).where(BackgroundJob.category == "email_analysis")).one()
    read = AsyncMock(return_value=PanelRead(reads=[BlindRead(what_it_sells="A course", pull=5)]))
    monkeypatch.setattr(analysis.BlindReader, "read", read)
    monkeypatch.setenv("JOB_HOST", "true")
    await jobs.execute(session.get_bind(), row.id, provider, None)
    await jobs.execute(session.get_bind(), row.id, provider, None)
    session.expire_all()
    assert session.get(EmailAnalysis, run.id).state == "completed"
    assert not session.get(BackgroundJob, row.id).active
    assert read.await_count == 1
