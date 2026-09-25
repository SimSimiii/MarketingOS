# ruff: noqa: F811
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

import pytest
from sqlmodel import Session, select

from app.auth import service as auth
from app.models.campaign_execution import CampaignExecution
from app.models.enums import ExecutionStatus
from app.models.user import User, UserSession
from app.runtime.work_limits import Reservation, WorkLimitError
from tests.api.test_auth import as_account, locked_client, open_signup  # noqa: F401


def test_library_and_brand_sources_are_private_even_in_unbranded_campaigns(locked_client):
    client = locked_client
    alice = as_account(client, "alice@example.com")
    bob = as_account(client, "bob@example.com")
    brand = client.post("/api/brands", headers=bob, json={"name": "Bob"}).json()["id"]
    own = client.post("/api/campaigns", headers=alice,
                      json={"name": "Alice", "request": "Write one email"}).json()["id"]
    foreign_ids = []
    for scope in ({}, {"brand_id": brand}):
        response = client.post("/api/knowledge", headers=bob,
                               json={**scope, "content": "BOB_PRIVATE_SOURCE"})
        assert response.status_code == 201
        foreign_ids.extend(row["id"] for row in response.json())
    assert client.get("/api/knowledge", headers=alice).json() == []
    assert client.get(f"/api/knowledge?campaign_id={own}", headers=alice).json() == []
    for identifier in foreign_ids:
        assert client.get(f"/api/knowledge/{identifier}", headers=alice).status_code == 404
        assert client.delete(f"/api/knowledge/{identifier}", headers=alice).status_code == 404
        assert client.get(f"/api/knowledge/{identifier}", headers=bob).status_code == 200


def test_global_running_and_market_jobs_only_show_owned_resources(locked_client, engine, monkeypatch):
    from app.services import market_service
    client = locked_client
    alice = as_account(client, "alice@example.com")
    bob = as_account(client, "bob@example.com")
    brand = client.post("/api/brands", headers=bob, json={"name": "Bob"}).json()["id"]
    campaign = client.post("/api/campaigns", headers=bob,
                          json={"name": "Bob", "request": "Write one email"}).json()["id"]
    with Session(engine) as db:
        db.add(CampaignExecution(campaign_id=UUID(campaign), status=ExecutionStatus.RUNNING))
        db.commit()
    monkeypatch.setattr(market_service, "_jobs", {
        UUID(brand): market_service.JobStatus(kind="scan", brand_id=UUID(brand)),
    })
    assert client.get("/api/executions/running", headers=alice).json() == []
    assert client.get("/api/market/jobs", headers=alice).json() == []
    assert len(client.get("/api/executions/running", headers=bob).json()) == 1
    assert len(client.get("/api/market/jobs", headers=bob).json()) == 1


@pytest.mark.parametrize("key,value", [("max_revisions", -1), ("draft_candidates", 999),
                                     ("max_total_tokens", None), ("max_duration_seconds", 99999)])
def test_policy_rejects_invalid_merged_values(client, key, value):
    campaign = client.post("/api/campaigns", json={"name": "Test", "request": "Write one email"}).json()["id"]
    response = client.put(f"/api/campaigns/{campaign}/policy",
                          json={"preset": "balanced", "overrides": {key: value}})
    assert response.status_code == 422


def test_refresh_rotation_has_exactly_one_winner(engine):
    with Session(engine) as db:
        user = User(email="rotation@example.com", password_hash="unused")
        db.add(user)
        db.commit()
        raw = auth.issue_tokens(db, user).refresh_token
    def rotate(_):
        with Session(engine) as db:
            try:
                auth.refresh(db, raw)
                return True
            except auth.AuthError:
                return False
    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(rotate, range(2))) == [False, True]
    with Session(engine) as db:
        assert len(db.exec(select(UserSession).where(UserSession.revoked_at == None)).all()) == 1


def test_quota_reserves_once_and_refunds_only_before_a_model_attempt(engine):
    with Session(engine) as db:
        user = User(email="quota@example.com", password_hash="unused", monthly_run_quota=1)
        db.add(user)
        db.commit()
        owner = user.id
    first = Reservation(engine, owner)
    try:
        with pytest.raises(WorkLimitError):
            Reservation(engine, owner)
    finally:
        first.finish()
    second = Reservation(engine, owner)
    second.attempt()
    second.finish()
    with pytest.raises(WorkLimitError):
        Reservation(engine, owner)


def test_lambda_refuses_model_work_before_creating_a_run(client, monkeypatch):
    campaign = client.post("/api/campaigns", json={"name": "Test", "request": "Write one email"}).json()["id"]
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "test-host")
    assert client.post(f"/api/campaigns/{campaign}/start").status_code == 503
    assert client.get(f"/api/campaigns/{campaign}/executions").json() == []


def test_campaign_pages_are_stable_and_filter_before_limiting(client):
    brand = client.post("/api/brands", json={"name": "Paged"}).json()["id"]
    for number in range(5):
        client.post("/api/campaigns", json={"name": f"Campaign {number}",
                    "request": "Write one email", "brand_id": brand if number % 2 else None})
    first = client.get("/api/campaigns?limit=2").json()
    second = client.get("/api/campaigns?limit=2&offset=2").json()
    assert len(first) == len(second) == 2
    assert not {row["id"] for row in first} & {row["id"] for row in second}
    scoped = client.get(f"/api/campaigns?brand_id={brand}&limit=2").json()
    assert len(scoped) == 2 and all(row["brand_id"] == brand for row in scoped)
    assert client.get("/api/campaigns?limit=99999").status_code == 422
    assert client.get("/api/knowledge?offset=-1").status_code == 422


def test_brand_sources_include_documents_attached_only_to_its_campaign(client):
    brand = client.post("/api/brands", json={"name": "Scoped"}).json()["id"]
    campaign = client.post("/api/campaigns", json={"name": "Scoped campaign",
                           "request": "Write one email", "brand_id": brand}).json()["id"]
    source = client.post("/api/knowledge", json={"campaign_id": campaign,
                         "content": "Campaign source shared with its brand"}).json()[0]
    rows = client.get(f"/api/knowledge?brand_id={brand}").json()
    assert [row["id"] for row in rows] == [source["id"]]


def test_qualification_sql_cost_does_not_grow_with_company_count(engine):
    from uuid import uuid4

    from sqlalchemy import event

    from app.models.market import ProspectRow
    from app.services.market_service import MarketService

    counts = []
    brand = uuid4()
    def count(*args):
        counts.append(1)
    event.listen(engine, "before_cursor_execute", count)
    try:
        with Session(engine) as db:
            service = MarketService(db)
            rows = [ProspectRow(brand_id=brand, segment="Dentists") for _ in range(100)]
            service.current_company_qualifications(brand, rows[:1])
            first = len(counts)
            counts.clear()
            result = service.current_company_qualifications(brand, rows)
            assert len(result) == 100
            # Profile, research, demand map and manually defined audiences.
            assert len(counts) == first == 4
    finally:
        event.remove(engine, "before_cursor_execute", count)


def test_cookie_alone_cannot_authorize_mutations_and_query_tokens_are_ignored(locked_client):
    client = locked_client
    headers = as_account(client, "cookie@example.com")
    raw = headers["Authorization"].removeprefix("Bearer ")
    client.cookies.clear()
    assert client.get(f"/api/auth/me?access_token={raw}").status_code == 401
    client.cookies.set("mos_access_token", raw)
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/brands", json={"name": "Cross site"}).status_code == 403
    assert client.post("/api/brands", json={"name": "Explicit"}, headers=headers).status_code == 201


def test_a_job_host_lambda_may_admit_model_work(monkeypatch):
    """The campaign state machine's three functions run on Lambda and do model
    work, which the blanket refusal above would make impossible.

    They opt in with JOB_HOST, and they may because each one is invoked with a
    single email to write - ten to thirty-five calls, roughly four minutes -
    which finishes well inside the 900-second ceiling. The API function does
    not set it and must not: it answers a button press behind a 30-second
    gateway timeout.
    """
    from app.runtime.work_limits import is_job_host

    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    monkeypatch.delenv("JOB_HOST", raising=False)
    assert is_job_host() is True, "anything that is not Lambda owns its own uptime"

    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "marketingos-api-prod")
    assert is_job_host() is False, "a plain Lambda still refuses"

    monkeypatch.setenv("JOB_HOST", "true")
    assert is_job_host() is True, "a step of the state machine may"


def test_a_resumed_reservation_does_not_charge_the_quota_again(engine):
    """A stepped run is one campaign spread over several invocations, and the
    user bought one campaign. Charging per step would make a five-email run
    cost seven runs against the account."""
    with Session(engine) as db:
        user = User(email="stepped@example.com", password_hash="unused", monthly_run_quota=10)
        db.add(user)
        db.commit()
        owner = user.id
        before = user.runs_used

    first = Reservation(engine, owner)
    first.attempt()
    with Session(engine) as db:
        charged = db.get(User, owner).runs_used
    assert charged == before + 1, "the plan step charges the run"
    first.finish()

    resumed = Reservation(engine, owner, resume=True)
    resumed.attempt()
    with Session(engine) as db:
        assert db.get(User, owner).runs_used == charged, "a craft step must not charge again"
    resumed.finish()

    with Session(engine) as db:
        assert db.get(User, owner).runs_used == charged, "and must not refund on close"
