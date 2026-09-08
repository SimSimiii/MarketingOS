"""Test bootstrap for the back-office.

Runs before any test module is imported, which matters for the same reason it
does in the product's suite: `app.core.database` resolves settings at import
time, so the only way to stop these tests binding to a real database is to fix
the environment before anything imports it.
"""

import os
import sys
from pathlib import Path

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ENVIRONMENT"] = "test"

# The product package is vendored beside this one at build time; in a checkout
# it lives in the sibling backend/.
_BACKEND = Path(__file__).resolve().parents[3] / "backend"
if (_BACKEND / "app").is_dir():
    sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from app.core.config import get_settings
from app.models.admin import AdminUser
from app.models.enums import AdminRole
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from admin.auth import hash_password
from admin.db import get_session
from admin.main import app

get_settings.cache_clear()

ADMIN_PASSWORD = "an-operator-password"


@pytest.fixture
def engine(tmp_path):
    """A real SQLite file, one connection per session - the same reasoning as
    the product's API suite: an in-memory StaticPool would hand every session
    the same connection and make two transactions into one."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'admin-test.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine):
    def override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def make_admin(session: Session, email: str, role: AdminRole) -> AdminUser:
    admin = AdminUser(
        email=email, password_hash=hash_password(ADMIN_PASSWORD), role=role, full_name="Operator"
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin


@pytest.fixture
def sign_in(client, session):
    """Return a callable that creates an operator at a role and signs them in."""

    def _sign_in(role: AdminRole = AdminRole.SUPERADMIN, email: str | None = None):
        address = email or f"{role}@example.com"
        make_admin(session, address, role)
        response = client.post(
            "/api/auth/login", json={"email": address, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _sign_in
