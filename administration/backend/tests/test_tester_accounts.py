"""Operators create the accounts testers sign in with; public signup stays shut."""

from __future__ import annotations

import pytest
from app.auth import service as platform_auth
from app.core.config import get_settings
from app.models.admin import AdminAuditLog
from app.models.enums import AdminRole
from sqlmodel import select

from admin.config import get_admin_settings


@pytest.fixture
def platform_pepper(monkeypatch):
    """The console holding the same pepper the platform verifies with."""
    monkeypatch.setattr(
        get_admin_settings(), "platform_password_pepper", get_settings().password_pepper
    )


def test_a_generated_password_is_shown_once_and_signs_in_on_the_platform(
    client, session, sign_in, platform_pepper
):
    response = client.post(
        "/api/users",
        json={"email": "Tester@Example.com", "full_name": "Tess", "plan": "pro"},
        headers=sign_in(AdminRole.ADMIN),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    password = body["generated_password"]
    assert password and len(password) >= 10
    assert body["user"]["email"] == "tester@example.com"
    assert body["user"]["plan"] == "pro"
    user = platform_auth.authenticate(session, email="tester@example.com", password=password)
    assert user.full_name == "Tess"


def test_a_chosen_password_is_used_and_never_echoed(client, session, sign_in, platform_pepper):
    response = client.post(
        "/api/users",
        json={"email": "chosen@example.com", "password": "a-chosen-password"},
        headers=sign_in(AdminRole.ADMIN),
    )

    assert response.status_code == 201
    assert response.json()["generated_password"] is None
    assert "a-chosen-password" not in response.text
    platform_auth.authenticate(session, email="chosen@example.com", password="a-chosen-password")


def test_the_creation_is_audited_without_the_password(client, session, sign_in, platform_pepper):
    client.post(
        "/api/users",
        json={"email": "audited@example.com", "password": "a-chosen-password"},
        headers=sign_in(AdminRole.ADMIN),
    )

    row = session.exec(select(AdminAuditLog).where(AdminAuditLog.action == "user.create")).one()
    assert row.detail["email"] == "audited@example.com"
    assert "a-chosen-password" not in str(row.detail)


def test_support_cannot_create_and_an_address_cannot_be_taken_twice(
    client, sign_in, platform_pepper
):
    body = {"email": "twice@example.com", "password": "a-chosen-password"}

    assert client.post("/api/users", json=body, headers=sign_in(AdminRole.SUPPORT)).status_code == 403
    admin = sign_in(AdminRole.ADMIN)
    assert client.post("/api/users", json=body, headers=admin).status_code == 201
    assert client.post("/api/users", json=body, headers=admin).status_code == 409


def test_without_the_platform_pepper_the_feature_is_off_rather_than_wrong(client, sign_in):
    """A hash made with the wrong pepper is an account nobody can sign in to."""
    response = client.post(
        "/api/users",
        json={"email": "nopepper@example.com", "password": "a-chosen-password"},
        headers=sign_in(AdminRole.ADMIN),
    )

    assert response.status_code == 503
