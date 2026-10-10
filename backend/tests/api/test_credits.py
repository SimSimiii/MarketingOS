"""Paid credit must be exact, signed at the route and idempotent in the ledger."""

import hashlib
import hmac
import json
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlmodel import Session

from app.ai.base import AIMessage, AIRequest
from app.ai.model_router import ModelRouter, ModelTier
from app.api.public_output import public_output
from app.auth.service import issue_tokens
from app.core.config import PROMPTS_DIR, get_settings
from app.models.credit import CreditCheckout
from app.models.enums import UserStatus
from app.models.user import User
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import get_prompt_engine
from app.schemas.campaign import AgentExecutionRead
from app.services.credit_meter import CreditMeter
from app.services.credit_service import (
    InsufficientCreditsError,
    assert_payment_mode_safe,
    balance,
    credit_paid_checkout,
    debit,
    freeze_reversed_payment,
    history,
)
from tests.marketing.conftest import RoleScriptedProvider


def _paid(checkout: CreditCheckout) -> dict:
    return {
        "id": checkout.stripe_session_id,
        "mode": "payment",
        "payment_status": "paid",
        "amount_total": checkout.amount_cents,
        "currency": checkout.currency,
        "livemode": checkout.livemode,
        "payment_intent": f"pi_{checkout.stripe_session_id}",
    }


def test_paid_checkout_credits_once_and_debit_is_atomic(engine):
    user = User(email="credits@example.com", password_hash="unused")
    checkout = CreditCheckout(
        stripe_session_id="cs_test_example", user_id=user.id,
        credits=1000, amount_cents=1000,
    )
    with Session(engine) as session:
        session.add(user)
        session.flush()
        session.add(checkout)
        session.commit()
        assert credit_paid_checkout(session, _paid(checkout))
        assert balance(session, user.id) == 1000
        assert not credit_paid_checkout(session, _paid(checkout))
        assert balance(session, user.id) == 1000
        assert debit(session, user.id, 225, "run:example") == 775
        assert debit(session, user.id, 225, "run:example") == 775
        assert [row.amount for row in history(session, user.id)] == [-225, 1000]
        assert_payment_mode_safe(session, live=False)
        with pytest.raises(RuntimeError, match="other Stripe mode"):
            assert_payment_mode_safe(session, live=True)
        with pytest.raises(InsufficientCreditsError):
            debit(session, user.id, 776, f"run:{uuid4()}")
        session.rollback()
        assert balance(session, user.id) == 775


def test_unpaid_or_wrong_amount_cannot_credit(engine):
    user = User(email="wrong@example.com", password_hash="unused")
    checkout = CreditCheckout(
        stripe_session_id="cs_test_wrong", user_id=user.id,
        credits=3000, amount_cents=3000,
    )
    with Session(engine) as session:
        session.add(user)
        session.flush()
        session.add(checkout)
        session.commit()
        for changed in ({"payment_status": "unpaid"}, {"amount_total": 1},
                        {"currency": "eur"}, {"mode": "subscription"},
                        {"livemode": True}):
            with pytest.raises(ValueError):
                credit_paid_checkout(session, {**_paid(checkout), **changed})
            session.rollback()
        assert balance(session, user.id) == 0


def test_refund_freezes_account_and_prevents_repeat_usage(engine):
    user = User(email="reversed@example.com", password_hash="unused")
    checkout = CreditCheckout(
        stripe_session_id="cs_test_reversed", user_id=user.id,
        credits=1000, amount_cents=1000,
    )
    with Session(engine) as session:
        session.add(user)
        session.flush()
        session.add(checkout)
        session.commit()
        assert credit_paid_checkout(session, _paid(checkout))
        assert freeze_reversed_payment(session, "pi_cs_test_reversed")
        assert not freeze_reversed_payment(session, "pi_cs_test_reversed")
        assert session.get(User, user.id).status == UserStatus.SUSPENDED
        assert balance(session, user.id) == 1000
        assert [row.kind for row in history(session, user.id)] == ["payment_reversed", "purchase"]
    with pytest.raises(ValueError, match="cannot use credits"):
        CreditMeter(f"vision:{user.id}", engine).reserve(AIRequest(model="gpt-5.6-sol"))


def test_reversal_arriving_before_checkout_cannot_grant_credit(engine):
    user = User(email="early-reversal@example.com", password_hash="unused")
    checkout = CreditCheckout(
        stripe_session_id="cs_test_early", user_id=user.id,
        credits=1000, amount_cents=1000,
    )
    with Session(engine) as session:
        session.add(user)
        session.flush()
        session.add(checkout)
        session.commit()
        assert not freeze_reversed_payment(session, "pi_cs_test_early")
        assert not credit_paid_checkout(session, _paid(checkout))
        assert balance(session, user.id) == 0


def test_customer_event_redaction_and_model_catalog_hidden(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "credit_billing_enabled", True)
    assert public_output({
        "type": "model_call_finished", "model": "gpt-5.6-sol",
        "message": "gpt-5.6-sol used 100 tokens", "input_tokens": 100,
        "nested": [{"cost_usd": 1.5, "message": "Done"}],
    }) == {"type": "model_call_finished", "message": "Step completed",
           "nested": [{"message": "Done"}]}
    assert client.get("/api/models").status_code == 404
    assert client.get("/api/linkedin/runs").status_code == 404
    assert client.post("/api/campaigns", json={
        "name": "Hidden model", "request": "Write an email about our product.",
        "model_overrides": {"*": "opus"},
    }).status_code == 422
    agent = AgentExecutionRead(
        id=uuid4(), agent_id="writer", agent_name="Writer", sequence_order=1,
        status="completed", input_data=None, output_data=None,
        error_message=None, started_at=None, completed_at=None,
        model="gpt-5.6-sol", input_tokens=100, output_tokens=50,
        cost_usd=1.5, duration_ms=10, attempt=1,
    )
    public = agent.model_dump(mode="json")
    assert public["model"] is None
    assert public["input_tokens"] == 0
    assert public["cost_usd"] == 0


def test_webhook_rejects_bad_signature_and_replay_credits_once(client, engine, monkeypatch):
    secret = "whsec_test_credit_event"
    monkeypatch.setattr(get_settings(), "stripe_webhook_secret", secret)
    user = User(email="signed@example.com", password_hash="unused")
    user_id = user.id
    with Session(engine) as session:
        session.add(user)
        session.flush()
        session.add(CreditCheckout(
            stripe_session_id="cs_test_signed", user_id=user.id,
            credits=1000, amount_cents=1000,
        ))
        session.commit()
    payload = json.dumps({
        "id": "evt_test_signed", "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_test_signed", "mode": "payment", "payment_status": "paid",
            "amount_total": 1000, "currency": "usd", "payment_intent": "pi_cs_test_signed",
            "livemode": False,
        }},
    }).encode()
    timestamp = int(time.time())
    signature = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    endpoint = "/api/credits/webhook"
    invalid = client.post(endpoint, content=payload,
                          headers={"Stripe-Signature": f"t={timestamp},v1=wrong"})
    assert invalid.status_code == 400
    header = {"Stripe-Signature": f"t={timestamp},v1={signature}"}
    assert client.post(endpoint, content=payload, headers=header).status_code == 200
    assert client.post(endpoint, content=payload, headers=header).status_code == 200
    with Session(engine) as session:
        assert balance(session, user_id) == 1000
        assert len(history(session, user_id)) == 1


def test_checkout_price_is_server_owned_and_test_mode_recorded(client, engine, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "credit_billing_enabled", True)
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_fake")
    user = User(email="checkout@example.com", password_hash="unused")
    with Session(engine) as db:
        db.add(user)
        db.commit()
        token = issue_tokens(db, user).access_token
    headers = {"Authorization": f"Bearer {token}"}
    seen = []

    def fake_create(**kwargs):
        seen.append(kwargs)
        return SimpleNamespace(id="cs_test_checkout", url="https://checkout.stripe.com/test", livemode=False)

    monkeypatch.setattr("app.api.routes.credits.stripe.checkout.Session.create", fake_create)
    assert client.post("/api/credits/checkout", json={"package": "other"}, headers=headers).status_code == 422
    response = client.post("/api/credits/checkout", json={"package": "starter"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["url"] == "https://checkout.stripe.com/test"
    assert seen[0]["line_items"][0]["price_data"]["unit_amount"] == 1000
    with Session(engine) as db:
        checkout = db.get(CreditCheckout, "cs_test_checkout")
        assert checkout is not None
        assert checkout.user_id == user.id and not checkout.livemode
        assert balance(db, user.id) == 0


def test_model_call_reserves_before_spend_and_releases_unused_credits(engine):
    user = User(email="meter@example.com", password_hash="unused")
    user_id = user.id
    with Session(engine) as session:
        session.add(user)
        session.flush()
        checkout = CreditCheckout(
            stripe_session_id="cs_test_meter", user_id=user_id,
            credits=1000, amount_cents=1000,
        )
        session.add(checkout)
        session.commit()
        credit_paid_checkout(session, _paid(checkout))
    meter = CreditMeter(f"vision:{user_id}", engine)
    request = AIRequest(
        model="gpt-5.6-sol", max_tokens=100,
        system_prompt="Read this page.",
        messages=[AIMessage(role="user", content="One short answer.")],
    )
    hold = meter.reserve(request)
    with Session(engine) as session:
        assert balance(session, user_id) == 1000 - hold.amount
    meter.settle(hold, 0.10)
    with Session(engine) as session:
        assert balance(session, user_id) == 980  # 2 × $0.10
    with pytest.raises(ValueError, match="verified prepaid price"):
        meter.reserve(request.model_copy(update={"model": "unknown-model"}))


def test_model_call_with_no_balance_never_reaches_provider(engine):
    user = User(email="empty@example.com", password_hash="unused")
    user_id = user.id
    with Session(engine) as session:
        session.add(user)
        session.commit()
    meter = CreditMeter(f"vision:{user_id}", engine)
    with pytest.raises(InsufficientCreditsError):
        meter.reserve(AIRequest(model="gpt-5.6-sol"))


@pytest.mark.asyncio
async def test_model_session_checks_credit_before_provider_call(engine, monkeypatch):
    import app.services.credit_meter as meter_module

    monkeypatch.setattr(meter_module, "app_engine", engine)
    monkeypatch.setattr(get_settings(), "credit_billing_enabled", True)
    user = User(email="runtime@example.com", password_hash="unused")
    user_id = user.id
    with Session(engine) as db:
        db.add(user)
        db.commit()
    provider = RoleScriptedProvider({"email_writer": "A short draft."})
    model = ModelSession(
        provider, get_prompt_engine(PROMPTS_DIR), EventBus(),
        ModelRouter({"*": "gpt-5.6-sol"}), f"vision:{user_id}",
    )
    with pytest.raises(Exception, match="Insufficient credits"):
        await model.text(role="email_writer", tier=ModelTier.DEEP,
                         system_prompt="Write clearly.", task="One sentence.")
    assert provider.requests == []


@pytest.mark.asyncio
async def test_model_session_settles_successful_call_to_twice_its_cost(engine, monkeypatch):
    import app.services.credit_meter as meter_module

    monkeypatch.setattr(meter_module, "app_engine", engine)
    monkeypatch.setattr(get_settings(), "credit_billing_enabled", True)
    user = User(email="paid-runtime@example.com", password_hash="unused")
    user_id = user.id
    with Session(engine) as db:
        db.add(user)
        db.flush()
        checkout = CreditCheckout(
            stripe_session_id="cs_test_paid_runtime", user_id=user_id,
            credits=1000, amount_cents=1000,
        )
        db.add(checkout)
        db.commit()
        credit_paid_checkout(db, _paid(checkout))
    provider = RoleScriptedProvider({"email_writer": "A short draft."})
    model = ModelSession(
        provider, get_prompt_engine(PROMPTS_DIR), EventBus(),
        ModelRouter({"*": "gpt-5.6-sol"}), f"vision:{user_id}",
    )
    result = await model.text(role="email_writer", tier=ModelTier.DEEP,
                              system_prompt="Write clearly.", task="One sentence.")
    assert result == "A short draft."
    assert len(provider.requests) == 1
    with Session(engine) as db:
        movements = history(db, user_id)
        assert sorted(item.kind for item in movements) == ["hold", "purchase", "release"]
        assert balance(db, user_id) == sum(item.amount for item in movements)
        assert balance(db, user_id) < 1000
