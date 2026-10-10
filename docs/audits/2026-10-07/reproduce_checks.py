"""Offline audit probes. Creates only disposable SQLite databases; no model/network calls.

Run from the repository root with backend/.venv/Scripts/python.exe and this path.
These check the current tree after fixes; baseline observations remain in preuves.json.
They are not a substitute for product regression tests.
"""
import json
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "administration/backend"))
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["CREDIT_BILLING_ENABLED"] = "false"
os.environ["AUTH_REQUIRED"] = "false"

# Repository rule: test bootstrap precedes any application import.
import tests.conftest  # noqa: F401,E402
from fastapi import HTTPException  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402
from app.core.database import create_app_engine  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.models.admin import AdminUser  # noqa: E402
from app.models.campaign import Campaign  # noqa: E402
from app.models.campaign_execution import CampaignExecution  # noqa: E402
from app.models.campaign_run_state import CampaignRunState  # noqa: E402
from app.models.credit import CreditAccount  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.campaign_service import CampaignService  # noqa: E402
from app.schemas.campaign import CampaignPolicyUpdate  # noqa: E402
from app.api.routes.campaigns import update_campaign_policy  # noqa: E402
from admin.service import delete_user  # noqa: E402
from step_handlers import _execution_id  # noqa: E402


def probes():
    findings = {}
    with tempfile.TemporaryDirectory(prefix="marketingos-audit-") as directory:
        engine = create_app_engine(f"sqlite:///{Path(directory).as_posix()}/audit.db")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            campaign = Campaign(name="Audit disposable", request="Write exactly 1 email.")
            db.add(campaign)
            db.commit()
            service = CampaignService(db, None)  # No provider is used by these CRUD operations.
            settings = get_settings()
            settings.credit_billing_enabled = True
            try:
                try:
                    update_campaign_policy(campaign.id, CampaignPolicyUpdate(overrides={
                        "model_overrides": {"*": "gpt-5.6-terra"}
                    }), service)
                    findings["nested_model_override_status"] = "accepted"
                except HTTPException as error:
                    findings["nested_model_override_status"] = error.status_code
            finally:
                settings.credit_billing_enabled = False
            execution = CampaignExecution(campaign_id=campaign.id)
            db.add(execution)
            db.commit()
            db.add(CampaignRunState(execution_id=execution.id))
            db.commit()
            try:
                service.delete_campaign(campaign)
                findings["campaign_with_run_state_delete"] = "deleted"
            except IntegrityError:
                db.rollback()
                findings["campaign_with_run_state_delete"] = "FOREIGN KEY constraint failed"
            admin = AdminUser(email="audit-admin@example.invalid", password_hash="unused")
            user = User(email="audit-user@example.invalid", password_hash="unused")
            db.add(admin)
            db.add(user)
            db.commit()
            db.add(CreditAccount(user_id=user.id, balance=1))
            db.commit()
            try:
                delete_user(db, admin, user, None)
                findings["credited_user_delete"] = "unexpected success"
            except IntegrityError:
                db.rollback()
                findings["credited_user_delete"] = "FOREIGN KEY constraint failed"
            except HTTPException as error:
                findings["credited_user_delete"] = error.status_code
        engine.dispose()
    execution_id = uuid4()
    findings["finish_accepts_preserved_id_with_step_error"] = _execution_id({
        "execution_id": str(execution_id),
        "step_error": {"Error": "States.TaskFailed", "Cause": "offline audit"},
    }) == execution_id
    findings["craft_catch_preserves_payload_in_template"] = (
        'ResultPath: $.step_error' in (ROOT / "backend/template.yaml").read_text(encoding="utf-8")
    )
    for filename in ("requirements.txt", "requirements.lock", "requirements-worker.txt"):
        content = (ROOT / "backend" / filename).read_text(encoding="utf-8")
        findings[f"stripe_in_{filename}"] = any(
            line.startswith("stripe==") for line in content.splitlines()
        )
    return findings


if __name__ == "__main__":
    print(json.dumps(probes(), indent=2))
