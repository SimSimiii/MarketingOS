"""The back-office, over HTTP.

The interesting assertions are the ones about the ladder - a support operator
can read every account and change none of them - and the ones about the audit
trail, which is only worth having if it cannot be skipped.
"""

from __future__ import annotations

import pytest
from app.auth import service as platform_auth
from app.auth.passwords import hash_password as platform_hash
from app.models.admin import AdminAuditLog
from app.models.brand import Brand
from app.models.enums import AdminRole, UserPlan, UserStatus
from app.models.user import User, UserSession
from sqlmodel import Session, select

from tests.conftest import ADMIN_PASSWORD, make_admin


@pytest.fixture
def customer(session: Session) -> User:
    user = User(
        email="founder@example.com",
        password_hash=platform_hash("a-customer-password"),
        full_name="Founder",
        company_name="Acme",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(Brand(name="Acme", owner_id=user.id))
    session.commit()
    return user


# ── Sign-in ──────────────────────────────────────────────────────────────────


def test_the_console_is_closed_without_a_token(client):
    for path in ("/api/overview", "/api/users", "/api/admins", "/api/audit"):
        assert client.get(path).status_code == 401, path


def test_a_platform_token_is_not_an_operator_token(client, session, customer):
    """The whole reason the two systems sign with different secrets."""
    tokens = platform_auth.issue_tokens(session, customer)
    response = client.get(
        "/api/overview", headers={"Authorization": f"Bearer {tokens.access_token}"}
    )
    assert response.status_code == 401


def test_signing_in_works_and_is_recorded(client, session, sign_in):
    headers = sign_in(AdminRole.ADMIN)
    assert client.get("/api/auth/me", headers=headers).json()["role"] == "admin"
    actions = [row.action for row in session.exec(select(AdminAuditLog))]
    assert "auth.login" in actions


def test_a_deactivated_operator_cannot_sign_in(client, session):
    admin = make_admin(session, "gone@example.com", AdminRole.ADMIN)
    admin.is_active = False
    session.add(admin)
    session.commit()
    response = client.post(
        "/api/auth/login", json={"email": "gone@example.com", "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 403


def test_a_wrong_password_and_an_unknown_operator_read_the_same(client, session):
    make_admin(session, "real@example.com", AdminRole.ADMIN)
    wrong = client.post(
        "/api/auth/login", json={"email": "real@example.com", "password": "not-the-password"}
    )
    unknown = client.post(
        "/api/auth/login", json={"email": "ghost@example.com", "password": ADMIN_PASSWORD}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


# ── Reading ──────────────────────────────────────────────────────────────────


def test_the_overview_counts_what_is_there(client, sign_in, customer):
    body = client.get("/api/overview", headers=sign_in()).json()
    assert body["users_total"] == 1
    assert body["users_active"] == 1
    assert body["brands_total"] == 1
    assert body["users_by_plan"]["free"] == 1
    # Priced from ADMIN_PLAN_PRICES, and free is free.
    assert body["estimated_mrr_usd"] == 0


def test_users_can_be_listed_searched_and_read(client, sign_in, customer):
    headers = sign_in()
    listing = client.get("/api/users", headers=headers).json()
    assert listing["total"] == 1
    assert listing["items"][0]["email"] == "founder@example.com"
    assert listing["items"][0]["brands"] == 1

    assert client.get("/api/users?search=acme", headers=headers).json()["total"] == 1
    assert client.get("/api/users?search=nobody", headers=headers).json()["total"] == 0
    assert client.get("/api/users?plan=pro", headers=headers).json()["total"] == 0

    detail = client.get(f"/api/users/{customer.id}", headers=headers).json()
    assert detail["company_name"] == "Acme"
    assert detail["active_sessions"] == 0
    assert detail["estimated_cost_usd"] == 0


def test_the_workspace_view_names_the_work_without_opening_it(client, sign_in, customer):
    body = client.get(f"/api/users/{customer.id}/workspace", headers=sign_in()).json()
    assert [brand["name"] for brand in body["brands"]] == ["Acme"]
    assert body["campaigns"] == []


def test_an_unknown_account_is_a_404(client, sign_in):
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/api/users/{missing}", headers=sign_in()).status_code == 404


# ── The ladder ───────────────────────────────────────────────────────────────


def test_support_can_read_everything_and_change_nothing(client, sign_in, customer):
    headers = sign_in(AdminRole.SUPPORT)
    assert client.get("/api/users", headers=headers).status_code == 200
    assert client.get("/api/audit", headers=headers).status_code == 200

    assert client.patch(
        f"/api/users/{customer.id}/plan", json={"plan": "pro"}, headers=headers
    ).status_code == 403
    assert client.post(
        f"/api/users/{customer.id}/suspend", json={}, headers=headers
    ).status_code == 403
    assert client.delete(f"/api/users/{customer.id}", headers=headers).status_code == 403


def test_deleting_an_account_is_superadmin_only(client, sign_in, customer):
    assert client.delete(
        f"/api/users/{customer.id}", headers=sign_in(AdminRole.ADMIN)
    ).status_code == 403


def test_creating_an_operator_is_superadmin_only(client, sign_in):
    payload = {"email": "new@example.com", "password": "a-long-enough-password", "role": "support"}
    assert client.post(
        "/api/admins", json=payload, headers=sign_in(AdminRole.ADMIN)
    ).status_code == 403


# ── Changing ─────────────────────────────────────────────────────────────────


def test_changing_a_plan_writes_the_before_and_after(client, session, sign_in, customer):
    headers = sign_in(AdminRole.ADMIN)
    response = client.patch(
        f"/api/users/{customer.id}/plan",
        json={"plan": "pro", "monthly_run_quota": 50, "reason": "paid invoice 12"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["plan"] == "pro"
    assert response.json()["monthly_run_quota"] == 50

    session.refresh(customer)
    assert customer.plan == UserPlan.PRO

    entry = session.exec(
        select(AdminAuditLog).where(AdminAuditLog.action == "user.plan_change")
    ).one()
    assert entry.detail["before"]["plan"] == "free"
    assert entry.detail["after"]["plan"] == "pro"
    assert entry.detail["reason"] == "paid invoice 12"
    assert entry.target_id == str(customer.id)


def test_a_quota_can_be_raised_and_the_period_handed_back(client, session, sign_in, customer):
    customer.runs_used = 9
    session.add(customer)
    session.commit()

    body = client.patch(
        f"/api/users/{customer.id}/quota",
        json={"monthly_run_quota": 100, "runs_used": 0, "reason": "failed batch"},
        headers=sign_in(AdminRole.ADMIN),
    ).json()
    assert body["monthly_run_quota"] == 100
    assert body["runs_used"] == 0


def test_suspending_an_account_ends_its_live_sessions(client, session, sign_in, customer):
    platform_auth.issue_tokens(session, customer)
    platform_auth.issue_tokens(session, customer)
    live = session.exec(
        select(UserSession).where(UserSession.user_id == customer.id, UserSession.revoked_at.is_(None))
    ).all()
    assert len(live) == 2

    response = client.post(
        f"/api/users/{customer.id}/suspend",
        json={"reason": "chargeback"},
        headers=sign_in(AdminRole.ADMIN),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "suspended"
    assert response.json()["suspended_reason"] == "chargeback"

    session.refresh(customer)
    assert customer.status == UserStatus.SUSPENDED
    still_live = session.exec(
        select(UserSession).where(UserSession.user_id == customer.id, UserSession.revoked_at.is_(None))
    ).all()
    assert still_live == []


def test_unsuspending_clears_the_reason(client, session, sign_in, customer):
    headers = sign_in(AdminRole.ADMIN)
    client.post(f"/api/users/{customer.id}/suspend", json={"reason": "spam"}, headers=headers)
    body = client.post(f"/api/users/{customer.id}/unsuspend", headers=headers).json()
    assert body["status"] == "active"
    assert body["suspended_reason"] is None


def test_forcing_a_sign_out_revokes_every_session(client, session, sign_in, customer):
    platform_auth.issue_tokens(session, customer)
    body = client.post(
        f"/api/users/{customer.id}/sign-out", headers=sign_in(AdminRole.ADMIN)
    ).json()
    assert body["sessions_revoked"] == 1


def test_deleting_an_account_keeps_its_work_and_unowns_it(client, session, sign_in, customer):
    brand_id = session.exec(select(Brand).where(Brand.owner_id == customer.id)).one().id
    user_id = customer.id

    response = client.delete(f"/api/users/{user_id}", headers=sign_in(AdminRole.SUPERADMIN))
    assert response.status_code == 200

    # The request ran on its own session; this one still has both rows in its
    # identity map, and `get` on a stale instance raises rather than
    # re-reading. Drop them so the assertions below see the database.
    session.expunge_all()
    assert session.get(User, user_id) is None

    orphan = session.get(Brand, brand_id)
    assert orphan is not None, "closing an account should not destroy the work in it"
    assert orphan.owner_id is None


# ── Operators ────────────────────────────────────────────────────────────────


def test_a_superadmin_can_create_and_update_operators(client, sign_in):
    headers = sign_in(AdminRole.SUPERADMIN)
    created = client.post(
        "/api/admins",
        json={"email": "new@example.com", "password": "a-long-enough-password", "role": "support"},
        headers=headers,
    )
    assert created.status_code == 201
    admin_id = created.json()["id"]

    duplicate = client.post(
        "/api/admins",
        json={"email": "NEW@example.com", "password": "a-long-enough-password"},
        headers=headers,
    )
    assert duplicate.status_code == 409

    promoted = client.patch(f"/api/admins/{admin_id}", json={"role": "admin"}, headers=headers)
    assert promoted.json()["role"] == "admin"


def test_a_short_operator_password_is_refused(client, sign_in):
    response = client.post(
        "/api/admins",
        json={"email": "weak@example.com", "password": "short"},
        headers=sign_in(AdminRole.SUPERADMIN),
    )
    assert response.status_code == 422


def test_an_operator_cannot_lock_themselves_out(client, session, sign_in):
    headers = sign_in(AdminRole.SUPERADMIN, email="boss@example.com")
    me = client.get("/api/auth/me", headers=headers).json()
    response = client.patch(f"/api/admins/{me['id']}", json={"is_active": False}, headers=headers)
    assert response.status_code == 400


def test_a_password_reset_never_records_the_password(client, session, sign_in):
    headers = sign_in(AdminRole.SUPERADMIN)
    created = client.post(
        "/api/admins",
        json={"email": "new@example.com", "password": "a-long-enough-password"},
        headers=headers,
    ).json()

    assert client.post(
        f"/api/admins/{created['id']}/password",
        json={"password": "a-different-long-password"},
        headers=headers,
    ).status_code == 204

    entry = session.exec(
        select(AdminAuditLog).where(AdminAuditLog.action == "admin.password_reset")
    ).one()
    assert "a-different-long-password" not in str(entry.detail)


# ── The trail ────────────────────────────────────────────────────────────────


def test_the_audit_log_reads_back_and_filters(client, sign_in, customer):
    headers = sign_in(AdminRole.ADMIN)
    client.patch(f"/api/users/{customer.id}/plan", json={"plan": "pro"}, headers=headers)
    client.post(f"/api/users/{customer.id}/suspend", json={}, headers=headers)

    everything = client.get("/api/audit", headers=headers).json()
    actions = {row["action"] for row in everything}
    assert {"auth.login", "user.plan_change", "user.suspend"} <= actions

    only_suspends = client.get("/api/audit?action=user.suspend", headers=headers).json()
    assert [row["action"] for row in only_suspends] == ["user.suspend"]

    by_target = client.get(f"/api/audit?target_id={customer.id}", headers=headers).json()
    assert len(by_target) == 2
    assert all(row["admin_email"] for row in by_target)


def test_the_timeseries_zero_fills_every_day(client, sign_in, customer):
    body = client.get("/api/stats/timeseries?metric=signups&days=7", headers=sign_in()).json()
    assert len(body["series"]) == 7
    assert sum(point["value"] for point in body["series"]) == 1


def test_an_unknown_metric_is_refused_rather_than_empty(client, sign_in):
    assert client.get(
        "/api/stats/timeseries?metric=nonsense", headers=sign_in()
    ).status_code == 400


def test_health_needs_no_token(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
