"""Durable authentication limits, with real concurrent SQLite sessions."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlmodel import Session, select

from app.auth import rate_limits
from app.auth.rate_limits import AuthThrottledError, password_attempt
from app.models.auth_rate_limit import AuthRateLimit


def attempt(session, email="person@example.com", namespace="customer.login", now=899):
    password_attempt(session, email=email, namespace=namespace, pepper="test-pepper", now=now)


def test_attempts_survive_session_changes_and_expire_without_locking_other_identities(engine, monkeypatch):
    monkeypatch.setattr(rate_limits, "PASSWORD_ATTEMPTS", 2)
    with Session(engine) as db:
        attempt(db)
    with Session(engine) as db:
        attempt(db, email=" Person@Example.com ")
        with pytest.raises(AuthThrottledError) as rejected:
            attempt(db)
        assert rejected.value.retry_after == 1
        attempt(db, email="other@example.com")
        attempt(db, namespace="admin.login")
        rows = db.exec(select(AuthRateLimit)).all()
        assert len(rows) == 3
        assert all("example.com" not in row.key and len(row.key) == 64 for row in rows)
    with Session(engine) as db:
        attempt(db, now=900)
        attempt(db, now=900)
        with pytest.raises(AuthThrottledError):
            attempt(db, now=900)


def test_parallel_sessions_cannot_each_claim_the_last_authentication_attempt(engine, monkeypatch):
    monkeypatch.setattr(rate_limits, "PASSWORD_ATTEMPTS", 3)

    def compete(_):
        with Session(engine) as db:
            try:
                attempt(db)
                return True
            except AuthThrottledError:
                return False

    with ThreadPoolExecutor(max_workers=6) as workers:
        assert sum(workers.map(compete, range(20))) == 3
    with Session(engine) as db:
        assert db.exec(select(AuthRateLimit)).one().attempts == 3


def test_old_attempt_identities_are_pruned(engine):
    with Session(engine) as db:
        attempt(db, email="old@example.com", now=0)
        attempt(db, email="recent@example.com", now=172800)
        rows = db.exec(select(AuthRateLimit)).all()
        assert len(rows) == 1
        assert rows[0].window_start == 172800


def test_http_login_limit_is_non_enumerating_and_ignores_forged_forwarded_headers(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "allow_public_signup", True)
    assert client.post("/api/auth/register", json={
        "email": "known@example.com", "password": "correct-test-password",
    }).status_code == 201
    monkeypatch.setattr(rate_limits, "PASSWORD_ATTEMPTS", 2)
    monkeypatch.setattr(rate_limits.time, "time", lambda: 899)
    blocked = []
    for email in ("Known@Example.com", "unknown@example.com"):
        for index in range(2):
            response = client.post("/api/auth/login", json={"email": email, "password": "wrong"},
                                   headers={"X-Forwarded-For": f"203.0.113.{index}"})
            assert response.status_code == 401
        response = client.post("/api/auth/login", json={"email": email.lower(), "password": "wrong"},
                               headers={"X-Forwarded-For": "198.51.100.1"})
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "1"
        blocked.append(response.json())
    assert blocked[0] == blocked[1]
    assert client.post("/api/auth/login", json={
        "email": "different@example.com", "password": "wrong",
    }).status_code == 401


@pytest.mark.parametrize("endpoint", ["login", "register"])
def test_oversized_password_is_rejected_before_hashing_or_account_creation(client, engine, endpoint):
    response = client.post(f"/api/auth/{endpoint}", json={
        "email": "oversized@example.com", "password": "a" * 4097,
    })
    assert response.status_code == 422
    with Session(engine) as db:
        assert db.exec(select(AuthRateLimit)).all() == []
