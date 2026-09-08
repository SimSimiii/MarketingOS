"""The account boundary, over HTTP.

Two separate questions are asked here and they are worth keeping apart:

- Can somebody sign in, refresh, and sign out? (`client` - auth is off, which
  is what a laptop install looks like.)
- Can one account reach another account's work? (`locked_client` - auth is on,
  which is what a deployment looks like.) That is the question the whole
  `owner_id` column exists to answer, so it is asked against brands, campaigns,
  market, knowledge and the activity log rather than once in general.
"""

import pytest
from fastapi.testclient import TestClient

from app.ai.factory import get_ai_provider
from app.core.config import get_settings
from app.core.database import get_session
from app.main import app
from tests.marketing.conftest import RoleScriptedProvider

PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def open_signup():
    """Registration is invite-only by default; these tests are about the flow."""
    settings = get_settings()
    before = settings.allow_public_signup
    settings.allow_public_signup = True
    yield
    settings.allow_public_signup = before


@pytest.fixture
def locked_client(provider: RoleScriptedProvider, engine, open_signup):
    """A client against a deployment that demands a token.

    `auth_required` is mutated on the cached settings object rather than
    through the environment because `get_settings` is `lru_cache`d and the app
    has already imported it - re-reading the environment here would need a
    process restart, which a test cannot do.
    """
    settings = get_settings()
    before = settings.auth_required
    settings.auth_required = True

    def session_override():
        from sqlmodel import Session

        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_ai_provider] = lambda: provider
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    settings.auth_required = before


def register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/auth/register", json={"email": email, "password": PASSWORD, "full_name": "Tester"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def as_account(client: TestClient, email: str) -> dict[str, str]:
    """Register and return the Authorization header for that account.

    The header, not the cookie the same call also set: the cookie is shared by
    every request this TestClient makes, so two accounts in one test would
    otherwise take turns being "the" signed-in one.
    """
    token = register(client, email)["access_token"]
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


# ── The flow ─────────────────────────────────────────────────────────────────


def test_registering_returns_a_usable_token(client: TestClient, open_signup):
    body = register(client, "founder@example.com")
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["user"]["email"] == "founder@example.com"
    assert body["user"]["plan"] == "free"
    assert "password" not in body["user"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "founder@example.com"


def test_signup_is_refused_when_the_deployment_is_invite_only(client: TestClient):
    response = client.post(
        "/api/auth/register", json={"email": "stranger@example.com", "password": PASSWORD}
    )
    assert response.status_code == 403


def test_the_same_address_cannot_register_twice(client: TestClient, open_signup):
    register(client, "founder@example.com")
    again = client.post(
        "/api/auth/register", json={"email": "FOUNDER@example.com", "password": PASSWORD}
    )
    assert again.status_code == 409


def test_a_short_password_is_refused_before_an_account_exists(client: TestClient, open_signup):
    response = client.post("/api/auth/register", json={"email": "a@example.com", "password": "abc"})
    assert response.status_code == 422
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": "abc"}).status_code == 401


def test_a_wrong_password_and_an_unknown_address_are_indistinguishable(
    client: TestClient, open_signup
):
    register(client, "founder@example.com")
    wrong = client.post("/api/auth/login", json={"email": "founder@example.com", "password": "nope-nope-nope"})
    unknown = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


def test_login_is_case_insensitive_on_the_address(client: TestClient, open_signup):
    register(client, "founder@example.com")
    response = client.post(
        "/api/auth/login", json={"email": "Founder@Example.COM", "password": PASSWORD}
    )
    assert response.status_code == 200


def test_refreshing_rotates_the_token_and_kills_the_old_one(client: TestClient, open_signup):
    first = register(client, "founder@example.com")
    client.cookies.clear()

    second = client.post("/api/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert second.status_code == 200
    assert second.json()["refresh_token"] != first["refresh_token"]

    client.cookies.clear()
    replayed = client.post("/api/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert replayed.status_code == 401


def test_signing_out_ends_that_session(client: TestClient, open_signup):
    body = register(client, "founder@example.com")
    client.cookies.clear()
    assert client.post("/api/auth/logout", json={"refresh_token": body["refresh_token"]}).status_code == 204
    assert client.post("/api/auth/refresh", json={"refresh_token": body["refresh_token"]}).status_code == 401


def test_changing_the_password_ends_every_other_session(client: TestClient, open_signup):
    body = register(client, "founder@example.com")
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {body['access_token']}"}

    changed = client.post(
        "/api/auth/password",
        json={"current_password": PASSWORD, "password": "a-brand-new-passphrase"},
        headers=headers,
    )
    assert changed.status_code == 204
    assert client.post("/api/auth/refresh", json={"refresh_token": body["refresh_token"]}).status_code == 401
    assert client.post(
        "/api/auth/login", json={"email": "founder@example.com", "password": "a-brand-new-passphrase"}
    ).status_code == 200


def test_a_wrong_current_password_does_not_change_anything(client: TestClient, open_signup):
    body = register(client, "founder@example.com")
    client.cookies.clear()
    response = client.post(
        "/api/auth/password",
        json={"current_password": "not-it-at-all", "password": "a-brand-new-passphrase"},
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert response.status_code == 400
    assert client.post(
        "/api/auth/login", json={"email": "founder@example.com", "password": PASSWORD}
    ).status_code == 200


def test_sessions_lists_where_the_account_is_signed_in(client: TestClient, open_signup):
    body = register(client, "founder@example.com")
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    client.post("/api/auth/login", json={"email": "founder@example.com", "password": PASSWORD})
    client.cookies.clear()

    sessions = client.get("/api/auth/sessions", headers=headers)
    assert sessions.status_code == 200
    assert len(sessions.json()) == 2

    assert client.post("/api/auth/logout-all", headers=headers).status_code == 204
    assert client.get("/api/auth/sessions", headers=headers).json() == []


# ── Single-user mode ─────────────────────────────────────────────────────────


def test_without_auth_required_the_api_still_answers_anonymously(client: TestClient):
    """The shape a laptop install keeps: no token, one workspace, no login."""
    assert client.get("/api/brands").status_code == 200
    assert client.get("/api/auth/config").json()["auth_required"] is False


def test_me_needs_an_account_even_where_auth_is_optional(client: TestClient):
    """Single-user mode has no account, so there is nothing to describe."""
    assert client.get("/api/auth/me").status_code == 401


# ── The boundary ─────────────────────────────────────────────────────────────


def test_a_locked_deployment_refuses_anonymous_requests(locked_client: TestClient):
    response = locked_client.get("/api/brands")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_a_garbled_token_is_refused(locked_client: TestClient):
    response = locked_client.get("/api/brands", headers={"Authorization": "Bearer not.a.token"})
    assert response.status_code == 401


def test_one_account_cannot_see_another_accounts_brand(locked_client: TestClient):
    alice = as_account(locked_client, "alice@example.com")
    created = locked_client.post("/api/brands", json={"name": "Alice Co"}, headers=alice)
    assert created.status_code == 201
    brand_id = created.json()["id"]

    bob = as_account(locked_client, "bob@example.com")
    assert locked_client.get("/api/brands", headers=bob).json() == []
    assert locked_client.get(f"/api/brands/{brand_id}", headers=bob).status_code == 404
    assert locked_client.get("/api/brands/overview", headers=bob).json() == []
    # Own brand still visible - the filter is a filter, not an outage.
    assert len(locked_client.get("/api/brands", headers=alice).json()) == 1


def test_another_accounts_brand_cannot_be_edited_or_deleted(locked_client: TestClient):
    alice = as_account(locked_client, "alice@example.com")
    brand_id = locked_client.post("/api/brands", json={"name": "Alice Co"}, headers=alice).json()["id"]

    bob = as_account(locked_client, "bob@example.com")
    assert locked_client.patch(
        f"/api/brands/{brand_id}/style", json={"primary_color": "#ff0000"}, headers=bob
    ).status_code == 404
    assert locked_client.delete(f"/api/brands/{brand_id}", headers=bob).status_code == 404
    assert locked_client.get(f"/api/brands/{brand_id}", headers=alice).status_code == 200


def test_the_market_router_is_closed_for_another_accounts_brand(locked_client: TestClient):
    alice = as_account(locked_client, "alice@example.com")
    brand_id = locked_client.post("/api/brands", json={"name": "Alice Co"}, headers=alice).json()["id"]

    bob = as_account(locked_client, "bob@example.com")
    for path in (
        f"/api/market/{brand_id}",
        f"/api/market/{brand_id}/rivals",
        f"/api/market/{brand_id}/audience",
        f"/api/market/{brand_id}/proof",
        f"/api/market/{brand_id}/radar",
    ):
        assert locked_client.get(path, headers=bob).status_code == 404, path
    assert locked_client.post(
        f"/api/market/{brand_id}/rivals", json={"name": "Rival"}, headers=bob
    ).status_code == 404


def test_a_campaign_cannot_be_attached_to_another_accounts_brand(locked_client: TestClient):
    alice = as_account(locked_client, "alice@example.com")
    brand_id = locked_client.post("/api/brands", json={"name": "Alice Co"}, headers=alice).json()["id"]

    bob = as_account(locked_client, "bob@example.com")
    response = locked_client.post(
        "/api/campaigns",
        json={"name": "Sneaky", "request": "Write 3 emails", "brand_id": brand_id},
        headers=bob,
    )
    assert response.status_code == 422


def test_one_account_cannot_see_another_accounts_campaign_or_its_runs(locked_client: TestClient):
    alice = as_account(locked_client, "alice@example.com")
    created = locked_client.post(
        "/api/campaigns", json={"name": "Launch", "request": "Write 3 emails"}, headers=alice
    )
    assert created.status_code == 201
    campaign_id = created.json()["id"]

    bob = as_account(locked_client, "bob@example.com")
    assert locked_client.get("/api/campaigns", headers=bob).json() == []
    assert locked_client.get(f"/api/campaigns/{campaign_id}", headers=bob).status_code == 404
    assert locked_client.delete(f"/api/campaigns/{campaign_id}", headers=bob).status_code == 404
    assert locked_client.get(f"/api/campaigns/{campaign_id}/executions", headers=bob).status_code == 404


def test_knowledge_cannot_be_filed_against_another_accounts_brand(locked_client: TestClient):
    alice = as_account(locked_client, "alice@example.com")
    brand_id = locked_client.post("/api/brands", json={"name": "Alice Co"}, headers=alice).json()["id"]

    bob = as_account(locked_client, "bob@example.com")
    assert locked_client.post(
        "/api/knowledge",
        json={"content": "Our product does X", "brand_id": brand_id, "title": "Notes"},
        headers=bob,
    ).status_code == 404
    assert locked_client.get(f"/api/knowledge?brand_id={brand_id}", headers=bob).status_code == 404
    assert locked_client.get(f"/api/knowledge/base?brand_id={brand_id}", headers=bob).status_code == 404


def test_settings_are_per_account(locked_client: TestClient):
    alice = as_account(locked_client, "alice@example.com")
    locked_client.patch("/api/settings", json={"company_name": "Alice Co"}, headers=alice)

    bob = as_account(locked_client, "bob@example.com")
    assert locked_client.get("/api/settings", headers=bob).json()["company_name"] is None
    assert locked_client.get("/api/settings", headers=alice).json()["company_name"] == "Alice Co"


def test_the_activity_log_only_shows_your_own_runs(locked_client: TestClient):
    alice = as_account(locked_client, "alice@example.com")
    locked_client.post(
        "/api/campaigns", json={"name": "Launch", "request": "Write 3 emails"}, headers=alice
    )
    bob = as_account(locked_client, "bob@example.com")
    assert locked_client.get("/api/logs", headers=bob).json() == []
