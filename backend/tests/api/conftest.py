"""HTTP-level fixtures: a real app, a real database, a scripted model."""

import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.ai.factory import get_ai_provider
from app.core.database import get_session
from app.main import app
from tests.marketing.conftest import RoleScriptedProvider, default_answers

POLL_TIMEOUT_SECONDS = 10


@pytest.fixture
def provider() -> RoleScriptedProvider:
    """Answers every role, so any campaign started in these tests finishes."""
    return RoleScriptedProvider(default_answers())


@pytest.fixture
def engine(tmp_path):
    """A real SQLite file, one connection per session.

    Deliberately not `sqlite://` on a `StaticPool`. That configuration hands
    every `Session(engine)` in the process the *same* DBAPI connection, and
    these tests always have at least two live at once: the request thread the
    `TestClient` drives and the background task running the campaign (see
    app.orchestration.execution_manager). Two sessions interleaving
    `commit()` and `rollback()` on one SQLite connection is one transaction,
    not two - so a commit in the run flushes the request's half-built rows
    and a rollback throws away the run's, which surfaces as
    `Could not refresh instance` on whichever row lost the race. That is the
    entire reason this suite was quarantined as "randomly flaky".

    A file-backed database gives each session its own connection and lets
    SQLite serialize the writers itself. WAL keeps a reader from blocking the
    writer, and the busy timeout absorbs the short overlaps that remain.
    """
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(connection, _record):  # pragma: no cover - driver glue
        cursor = connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(provider: RoleScriptedProvider, engine):
    def session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_ai_provider] = lambda: provider
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def create_campaign(client: TestClient, **overrides) -> dict:
    payload = {
        "name": "Launch",
        "request": "Write me 3 emails that make people buy my note-taking app",
        "product_description": "A note-taking app for developers",
    }
    payload.update(overrides)
    response = client.post("/api/campaigns", json=payload)
    assert response.status_code == 201, response.text
    campaign = response.json()

    # These tests are about the HTTP surface and the run's lifecycle. They
    # attach no material, which compiles to nothing a stranger could check -
    # the one case the preflight stop refuses to spend a run on, and it would
    # end every one of them before the first role turn. The stop is tested
    # where it belongs, against the pipeline.
    policy = client.put(
        f"/api/campaigns/{campaign['id']}/policy",
        json={"preset": "balanced", "overrides": {"require_proof": False}},
    )
    assert policy.status_code == 200, policy.text
    return policy.json()


def await_terminal_status(client: TestClient, execution_id: str) -> dict:
    """A campaign run happens in a background task (see
    app.orchestration.execution_manager), so /start returns immediately with
    status "running" - tests poll the same way a real client would."""
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        execution = client.get(f"/api/executions/{execution_id}/status").json()
        if execution["status"] not in ("pending", "running"):
            return execution
        time.sleep(0.02)
    raise AssertionError(f"Execution {execution_id} did not reach a terminal status in time")


def run_campaign(client: TestClient, **overrides) -> str:
    """Create a campaign, run it to a terminal state, return the execution id."""
    campaign = create_campaign(client, **overrides)
    started = client.post(f"/api/campaigns/{campaign['id']}/start")
    assert started.status_code == 202, started.text
    execution_id = started.json()["id"]
    await_terminal_status(client, execution_id)
    return execution_id
