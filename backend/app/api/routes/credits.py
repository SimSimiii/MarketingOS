"""Customer credit balance and signed Stripe top-ups."""

from datetime import datetime

import stripe
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from app.api.deps import CurrentUserDep, SessionDep
from app.core.config import assert_prepaid_prices_current, get_settings
from app.models.credit import CreditCheckout
from app.services.credit_service import (
    balance,
    credit_paid_checkout,
    freeze_reversed_payment,
    history,
)

router = APIRouter(prefix="/credits", tags=["credits"])

# One credit is $0.01. Keep package amounts server-owned: a browser never
# specifies either the charge or the number of credits it receives.
PACKAGES = {"starter": 1000, "standard": 3000, "growth": 6000}


class CreditMovement(BaseModel):
    amount: int
    balance_after: int
    kind: str
    created_at: datetime


class CreditBalance(BaseModel):
    balance: int
    unit: str = "credit"
    billing_active: bool
    movements: list[CreditMovement]


class CheckoutRequest(BaseModel):
    package: str


class CheckoutResponse(BaseModel):
    url: str


@router.get("", response_model=CreditBalance)
def read_credits(user: CurrentUserDep, session: SessionDep) -> CreditBalance:
    return CreditBalance(
        balance=balance(session, user.id),
        billing_active=get_settings().credit_billing_enabled,
        movements=[CreditMovement.model_validate(row, from_attributes=True)
                   for row in history(session, user.id)],
    )


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(data: CheckoutRequest, user: CurrentUserDep, session: SessionDep) -> CheckoutResponse:
    settings = get_settings()
    if (not settings.credit_billing_enabled or not settings.stripe_secret_key
            or not settings.stripe_webhook_secret):
        raise HTTPException(503, "Credit recharge is not configured yet.")
    try:
        assert_prepaid_prices_current()
    except RuntimeError as exc:
        raise HTTPException(503, "Credit purchases are temporarily paused for a pricing review.") from exc
    credits = PACKAGES.get(data.package)
    if credits is None:
        raise HTTPException(422, "Choose an available credit package.")
    stripe.api_key = settings.stripe_secret_key
    origin = settings.public_app_url.rstrip("/")
    try:
        checkout = stripe.checkout.Session.create(
            mode="payment",
            client_reference_id=str(user.id),
            customer_email=user.email,
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": credits,
                    "product_data": {"name": f"MarketingOS · {credits:,} credits"},
                },
                "quantity": 1,
            }],
            success_url=f"{origin}/settings?credits=return",
            cancel_url=f"{origin}/settings?credits=cancelled",
        )
    except stripe.StripeError as exc:
        raise HTTPException(502, "Could not start secure checkout. Please retry.") from exc
    if not checkout.id or not checkout.url:
        raise HTTPException(502, "Stripe did not return a checkout link.")
    expected_live = settings.stripe_secret_key.startswith("sk_live_")
    if bool(checkout.livemode) != expected_live:
        raise HTTPException(502, "Stripe mode did not match the configured billing key.")
    session.add(CreditCheckout(
        stripe_session_id=checkout.id,
        user_id=user.id,
        credits=credits,
        amount_cents=credits,
        livemode=bool(checkout.livemode),
    ))
    session.commit()
    return CheckoutResponse(url=checkout.url)


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request, session: SessionDep, stripe_signature: str | None = Header(None)
) -> dict[str, bool]:
    settings = get_settings()
    if not settings.stripe_webhook_secret or not stripe_signature:
        raise HTTPException(400, "Missing Stripe signature.")
    try:
        event = stripe.Webhook.construct_event(
            await request.body(), stripe_signature, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(400, "Invalid Stripe signature.") from exc
    if event["type"] in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        checkout = event["data"]["object"]
        # Delayed payment methods complete before they become paid.
        if checkout.get("payment_status") == "paid":
            try:
                credit_paid_checkout(session, checkout)
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc
    elif event["type"] in {"charge.refunded", "charge.dispute.created"}:
        charge = event["data"]["object"]
        intent = charge.get("payment_intent")
        if not isinstance(intent, str) and event["type"] == "charge.dispute.created":
            charge_id = charge.get("charge")
            if isinstance(charge_id, str) and settings.stripe_secret_key:
                stripe.api_key = settings.stripe_secret_key
                try:
                    intent = stripe.Charge.retrieve(charge_id).payment_intent
                except stripe.StripeError as exc:
                    raise HTTPException(503, "Could not verify disputed payment.") from exc
        if isinstance(intent, str):
            freeze_reversed_payment(session, intent)
    return {"received": True}
