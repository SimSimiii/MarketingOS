"""HTTP-level fixtures: a real app, a real database, a scripted model."""

import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
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
def engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
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
    return response.json()


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
