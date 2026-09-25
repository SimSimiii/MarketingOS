"""The first operator, created from inside the VPC by a function nobody can reach
over HTTP."""

from app.core import database
from app.models.admin import AdminUser
from sqlmodel import Session, select

from admin.auth import verify_password
from scripts.bootstrap_admin import lambda_handler

PASSWORD = "a-long-enough-password"


def test_the_handler_creates_a_superadmin_whose_password_verifies(engine, monkeypatch):
    monkeypatch.setattr(database, "engine", engine)

    result = lambda_handler({"email": "Ops@Example.com", "password": PASSWORD})

    assert result["ok"] is True
    assert PASSWORD not in str(result)
    with Session(engine) as session:
        admin = session.exec(select(AdminUser)).one()
    assert admin.email == "ops@example.com"
    assert admin.role == "superadmin"
    assert verify_password(PASSWORD, admin.password_hash)


def test_an_existing_operator_is_refused_unless_a_reset_is_asked_for(engine, monkeypatch):
    monkeypatch.setattr(database, "engine", engine)
    lambda_handler({"email": "ops@example.com", "password": PASSWORD})

    refused = lambda_handler({"email": "ops@example.com", "password": PASSWORD + "-2"})
    reset = lambda_handler(
        {"email": "ops@example.com", "password": PASSWORD + "-2", "reset_password": True}
    )

    assert refused["ok"] is False
    assert reset["ok"] is True
    with Session(engine) as session:
        admin = session.exec(select(AdminUser)).one()
    assert verify_password(PASSWORD + "-2", admin.password_hash)


def test_a_short_password_or_a_missing_field_writes_nothing(engine, monkeypatch):
    monkeypatch.setattr(database, "engine", engine)

    assert lambda_handler({"email": "ops@example.com", "password": "short"})["ok"] is False
    assert lambda_handler({"email": "ops@example.com"})["ok"] is False
    assert lambda_handler({"email": "ops@example.com", "password": PASSWORD, "role": "god"})[
        "ok"
    ] is False
    with Session(engine) as session:
        assert session.exec(select(AdminUser)).first() is None
