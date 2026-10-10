"""Regressions found during the pre-pilot audit; no external calls or payments."""

from datetime import date
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlmodel import Session, select

from app.ai.base import AIResponse, AIUsage
from app.ai.model_router import ModelRouter, ModelTier
from app.core.config import PROMPTS_DIR, get_settings
from app.models.campaign import Campaign
from app.models.campaign_execution import CampaignExecution
from app.models.campaign_run_state import CampaignRunState
from app.models.enums import ExecutionStatus
from app.models.user import User
from app.runtime.events import EventBus, ModelCallStarted
from app.runtime.exceptions import ProviderError
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import get_prompt_engine
from app.runtime.work_limits import WorkLimitError, current_work
from app.services.credit_service import balance, history, refund
from app.services.knowledge_service import KnowledgeService
from tests.marketing.conftest import RoleScriptedProvider


def test_delete_campaign_removes_durable_run_state(client, engine):
    campaign_id = UUID(client.post("/api/campaigns", json={
        "name": "Completed stepped run", "request": "Write one email.",
    }).json()["id"])
    with Session(engine) as db:
        execution = CampaignExecution(campaign_id=campaign_id, status=ExecutionStatus.COMPLETED)
        db.add(execution)
        db.flush()
        db.add(CampaignRunState(execution_id=execution.id))
        db.commit()
    assert client.delete(f"/api/campaigns/{campaign_id}").status_code == 204
    with Session(engine) as db:
        assert db.exec(select(CampaignRunState)).all() == []
        assert db.get(Campaign, campaign_id) is None


@pytest.mark.parametrize("settings_body", [
    {"model_overrides": {"email_writer": "gpt-5.6-terra"}},
    {"overrides": {"model_overrides": {"email_writer": "gpt-5.6-terra"}}},
])
def test_paid_policy_rejects_nested_and_direct_model_selection(client, monkeypatch, settings_body):
    campaign = client.post("/api/campaigns", json={
        "name": "Managed models", "request": "Write one email.",
    }).json()
    monkeypatch.setattr(get_settings(), "credit_billing_enabled", True)
    response = client.put(f"/api/campaigns/{campaign['id']}/policy", json=settings_body)
    assert response.status_code == 422
    assert "managed by the service" in response.json()["detail"]


def test_saved_model_override_is_rejected_before_paid_launch(client, monkeypatch, engine):
    campaign = client.post("/api/campaigns", json={
        "name": "Old model pin", "request": "Write one email.", "model_overrides": {"*": "opus"},
    }).json()
    monkeypatch.setattr(get_settings(), "credit_billing_enabled", True)
    assert client.post(f"/api/campaigns/{campaign['id']}/start").status_code == 422
    with Session(engine) as db:
        assert db.exec(select(CampaignExecution)).all() == []


@pytest.mark.parametrize("endpoint,method", [("/api/knowledge", "source"), ("/api/knowledge/upload", "upload")])
def test_empty_import_is_not_a_success(client, monkeypatch, endpoint, method):
    async def empty(*args, **kwargs):
        return []
    monkeypatch.setattr(KnowledgeService, f"ingest_{method}", empty)
    response = (client.post(endpoint, json={"url": "https://example.com"}) if method == "source"
                else client.post(endpoint, files={"file": ("empty.txt", b"", "text/plain")}))
    assert response.status_code == 422
    assert "No readable content" in response.json()["detail"]


@pytest.mark.parametrize("limit", [-1, 0, 501, 1000000])
def test_logs_limit_is_bounded(client, limit):
    assert client.get(f"/api/logs?limit={limit}").status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["admission", "event", "provider", "unknown_model", "unknown_version", "invalid_cost"])
async def test_credit_reserve_is_released_only_for_proven_unsent_calls(engine, monkeypatch, failure):
    import app.services.credit_meter as meter_module

    monkeypatch.setattr(meter_module, "app_engine", engine)
    monkeypatch.setattr(get_settings(), "credit_billing_enabled", True)
    user = User(email="reserve-test@example.com", password_hash="unused")
    user_id = user.id
    with Session(engine) as db:
        db.add(user)
        db.commit()
        refund(db, user_id, 1000, "audit:initial")

    class Provider(RoleScriptedProvider):
        async def generate(self, request):
            self.requests.append(request)
            if failure == "provider":
                # Same exception type as local admission, but the request did
                # reach the provider: this must keep its uncertain reserve.
                raise WorkLimitError("Remote operation stopped after send.")
            returned_model = {
                "unknown_model": "unpriced-future-model",
                "unknown_version": "claude-sonnet-future-unreviewed-version",
            }.get(failure, request.model)
            return AIResponse(
                content="Done", model=returned_model,
                usage=AIUsage(reported_cost_usd=float("nan") if failure == "invalid_cost" else 0.01),
            )

    provider = Provider({})
    events = EventBus()
    if failure == "event":
        def failed_log(event):
            raise RuntimeError("Execution logging failed before the request")
        events.subscribe(ModelCallStarted, failed_log)
    model = ModelSession(provider, get_prompt_engine(PROMPTS_DIR), events,
                         ModelRouter({"*": "gpt-5.6-sol"}), f"vision:{user_id}")

    def refuse():
        raise WorkLimitError("Server budget reached before send.")

    permit = SimpleNamespace(attempt=refuse, tokens=0) if failure == "admission" else None
    token = current_work.set(permit)
    try:
        with pytest.raises(ProviderError):
            await model.text(role="email_writer", tier=ModelTier.DEEP,
                             system_prompt="Write clearly", task="One sentence")
    finally:
        current_work.reset(token)
    with Session(engine) as db:
        assert (balance(db, user_id) == 1000) is (failure in {"admission", "event"})
        assert sum(item.amount for item in history(db, user_id)) == balance(db, user_id)
    assert len(provider.requests) == (0 if failure in {"admission", "event"} else 1)


@pytest.mark.parametrize("model,alias", [
    ("claude-haiku-4-5", "haiku"), ("claude-sonnet-5", "sonnet"),
    ("claude-opus-5", "opus"), ("claude-fable-5-1", "fable5"),
])
def test_paid_cost_recognizes_only_explicit_api_aliases(model, alias):
    from app.ai.anthropic_api_provider import resolve_model
    from app.services.credit_meter import CreditMeter

    assert resolve_model(alias) == model
    usage = AIUsage(reported_cost_usd=0.01)
    assert CreditMeter.measured_cost(model, usage) == 0.01


def test_expired_prices_block_new_purchases_but_keep_credit_reads_available(client, engine, monkeypatch):
    import app.core.config as config_module
    from app.auth.service import issue_tokens

    user = User(email="old-prices@example.com", password_hash="unused")
    with Session(engine) as db:
        db.add(user)
        db.commit()
        access = issue_tokens(db, user).access_token
    headers = {"Authorization": f"Bearer {access}"}
    monkeypatch.setattr(get_settings(), "credit_billing_enabled", True)
    monkeypatch.setattr(get_settings(), "stripe_secret_key", "sk_test_local")
    monkeypatch.setattr(get_settings(), "stripe_webhook_secret", "whsec_local")
    monkeypatch.setattr(config_module, "PREPAID_PRICES_REVIEWED_ON", date(2000, 1, 1))
    assert client.get("/api/credits", headers=headers).status_code == 200
    response = client.post("/api/credits/checkout", json={"package": "starter"}, headers=headers)
    assert response.status_code == 503
    assert "pricing review" in response.json()["detail"]


def test_reserve_release_is_idempotent(engine):
    from app.ai.base import AIRequest
    from app.services.credit_meter import CreditMeter

    user = User(email="release@example.com", password_hash="unused")
    user_id = user.id
    with Session(engine) as db:
        db.add(user)
        db.commit()
        refund(db, user_id, 1000, "release:initial")
    meter = CreditMeter(f"vision:{user_id}", engine)
    hold = meter.reserve(AIRequest(model="gpt-5.6-sol"))
    meter.release_unsent(hold)
    meter.release_unsent(hold)
    with Session(engine) as db:
        assert balance(db, user_id) == 1000


def test_edit_draft_preserves_sources_and_policy(client):
    campaign = client.post("/api/campaigns", json={
        "name": "Draft", "request": "Write one email.", "policy_preset": "fast",
    }).json()
    source = client.post("/api/knowledge", json={
        "campaign_id": campaign["id"], "content": "Original product evidence remains attached.",
    }).json()[0]
    response = client.put(f"/api/campaigns/{campaign['id']}/brief", json={
        "name": "Corrected draft", "request": "Write two emails for existing customers.",
        "cta_url": "https://example.com/new-destination", "goals": "Book a product tour",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Corrected draft"
    assert body["cta_url"] == "https://example.com/new-destination"
    assert body["policy"]["preset"] == "fast"
    assert client.get(f"/api/knowledge/{source['id']}").status_code == 200
    assert client.get(f"/api/campaigns/{campaign['id']}/executions").json() == []


def test_editing_does_not_rewrite_past_campaign_context(client, engine):
    campaign = client.post("/api/campaigns", json={"name": "Original", "request": "Write one email."}).json()
    with Session(engine) as db:
        db.add(CampaignExecution(campaign_id=UUID(campaign["id"]), status=ExecutionStatus.FAILED))
        db.commit()
    response = client.put(f"/api/campaigns/{campaign['id']}/brief", json={
        "name": "Replacement", "request": "Write two emails.",
    })
    assert response.status_code == 409
    assert client.get(f"/api/campaigns/{campaign['id']}").json()["name"] == "Original"


def test_brief_update_cannot_modify_ownership_or_models(client):
    campaign = client.post("/api/campaigns", json={"name": "Draft", "request": "Write one email."}).json()
    assert client.put(f"/api/campaigns/{campaign['id']}/brief", json={
        "name": "Changed", "request": "Write one email.", "model_overrides": {"*": "opus"},
    }).status_code == 422


def test_readiness_checks_database_without_calling_a_provider(client, monkeypatch):
    from sqlalchemy.exc import OperationalError

    assert client.get("/api/ready").json() == {"status": "ready"}

    def unavailable(*args, **kwargs):
        raise OperationalError("private-db-connection-info", {}, None)

    monkeypatch.setattr(Session, "exec", unavailable)
    response = client.get("/api/ready")
    assert response.status_code == 503
    assert "private-db-connection-info" not in response.text
