"""Atomic prepaid balance changes. One credit represents one US cent paid."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, col, select

from app.models.credit import (
    CreditAccount,
    CreditCheckout,
    CreditTransaction,
    ReversedStripePayment,
)
from app.models.enums import UserStatus
from app.models.user import User


class InsufficientCreditsError(ValueError):
    pass


def ensure_account(session: Session, user_id: UUID) -> CreditAccount:
    """Create the zero balance once, including when two workers race."""
    dialect = session.get_bind().dialect.name
    if dialect not in {"sqlite", "postgresql"}:
        raise RuntimeError(f"Credit accounting requires SQLite or PostgreSQL, got {dialect}.")
    insert = sqlite_insert if dialect == "sqlite" else pg_insert
    session.execute(
        insert(CreditAccount).values(user_id=user_id, balance=0, updated_at=datetime.now(UTC))
        .on_conflict_do_nothing(index_elements=["user_id"])
    )
    session.flush()
    account = session.get(CreditAccount, user_id)
    assert account is not None
    return account


def balance(session: Session, user_id: UUID) -> int:
    account = session.get(CreditAccount, user_id)
    return account.balance if account else 0


def history(session: Session, user_id: UUID, limit: int = 50) -> list[CreditTransaction]:
    return list(session.exec(
        select(CreditTransaction)
        .where(col(CreditTransaction.user_id) == user_id)
        .order_by(col(CreditTransaction.id).desc())
        .limit(limit)
    ))


def assert_payment_mode_safe(session: Session, *, live: bool) -> None:
    """Do not let test-funded balances become spendable with live API costs."""
    conflicting = session.exec(select(CreditCheckout.stripe_session_id).where(
        CreditCheckout.credited_at.is_not(None), CreditCheckout.livemode != live
    ).limit(1)).first()
    if conflicting is not None:
        raise RuntimeError("This database contains credits from the other Stripe mode. Use a separate billing database or reconcile it before activation.")


def _lock_payment(session: Session, payment_intent_id: str) -> None:
    """Serialize a paid checkout against its refund/dispute on PostgreSQL."""
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:intent, 0))"),
            {"intent": payment_intent_id},
        )


def debit(
    session: Session, user_id: UUID, amount: int, reference: str, *, kind: str = "usage"
) -> int:
    """Debit once. The conditional SQL update protects concurrent purchases."""
    if amount <= 0:
        raise ValueError("A debit must be positive.")
    prior = session.exec(select(CreditTransaction).where(
        col(CreditTransaction.reference) == reference
    )).first()
    if prior:
        if prior.user_id != user_id or prior.amount != -amount:
            raise ValueError("Credit reference reused for a different debit.")
        return prior.balance_after
    ensure_account(session, user_id)
    updated = session.execute(
        update(CreditAccount)
        .where(CreditAccount.user_id == user_id, CreditAccount.balance >= amount)
        .values(balance=CreditAccount.balance - amount, updated_at=datetime.now(UTC))
        .returning(CreditAccount.balance)
    ).scalar_one_or_none()
    if updated is None:
        raise InsufficientCreditsError("Insufficient credits. Recharge your balance to continue.")
    session.add(CreditTransaction(
        user_id=user_id, amount=-amount, balance_after=updated,
        kind=kind, reference=reference,
    ))
    session.commit()
    return updated


def refund(session: Session, user_id: UUID, amount: int, reference: str) -> int:
    """Release an unused call hold once, after a measured provider response."""
    if amount <= 0:
        raise ValueError("A refund must be positive.")
    prior = session.exec(select(CreditTransaction).where(
        col(CreditTransaction.reference) == reference
    )).first()
    if prior:
        if prior.user_id != user_id or prior.amount != amount:
            raise ValueError("Credit reference reused for a different refund.")
        return prior.balance_after
    ensure_account(session, user_id)
    updated = session.execute(
        update(CreditAccount)
        .where(CreditAccount.user_id == user_id)
        .values(balance=CreditAccount.balance + amount, updated_at=datetime.now(UTC))
        .returning(CreditAccount.balance)
    ).scalar_one()
    session.add(CreditTransaction(
        user_id=user_id, amount=amount, balance_after=updated,
        kind="release", reference=reference,
    ))
    session.commit()
    return updated


def credit_paid_checkout(session: Session, stripe_session: dict) -> bool:
    """Grant only a recorded, paid checkout with the exact expected amount.

    The conditional update of `credited_at` is the idempotency gate. Its
    transaction contains the balance increment and journal row, so a webhook
    retry or another worker cannot grant twice.
    """
    session_id = stripe_session.get("id")
    checkout = session.get(CreditCheckout, session_id) if isinstance(session_id, str) else None
    if checkout is None:
        raise ValueError("Unknown checkout session.")
    if (
        stripe_session.get("mode") != "payment"
        or stripe_session.get("payment_status") != "paid"
        or stripe_session.get("amount_total") != checkout.amount_cents
        or stripe_session.get("currency") != checkout.currency
        or stripe_session.get("livemode") is not checkout.livemode
        or not isinstance(stripe_session.get("payment_intent"), str)
    ):
        raise ValueError("Checkout payment does not match the recorded purchase.")
    _lock_payment(session, stripe_session["payment_intent"])
    if session.get(ReversedStripePayment, stripe_session["payment_intent"]) is not None:
        return False
    claimed = session.execute(
        update(CreditCheckout)
        .where(CreditCheckout.stripe_session_id == session_id,
               CreditCheckout.credited_at.is_(None))
        .values(credited_at=datetime.now(UTC),
                payment_intent_id=stripe_session["payment_intent"])
        .returning(CreditCheckout.stripe_session_id)
    ).scalar_one_or_none()
    if claimed is None:
        session.rollback()
        return False
    ensure_account(session, checkout.user_id)
    new_balance = session.execute(
        update(CreditAccount)
        .where(CreditAccount.user_id == checkout.user_id)
        .values(balance=CreditAccount.balance + checkout.credits,
                updated_at=datetime.now(UTC))
        .returning(CreditAccount.balance)
    ).scalar_one()
    session.add(CreditTransaction(
        user_id=checkout.user_id, amount=checkout.credits,
        balance_after=new_balance, kind="purchase", reference=f"stripe:{session_id}",
    ))
    session.commit()
    return True


def freeze_reversed_payment(session: Session, payment_intent_id: str) -> bool:
    """A refund or dispute immediately stops further usage pending review."""
    _lock_payment(session, payment_intent_id)
    dialect = session.get_bind().dialect.name
    insert = sqlite_insert if dialect == "sqlite" else pg_insert
    session.execute(
        insert(ReversedStripePayment)
        .values(payment_intent_id=payment_intent_id, created_at=datetime.now(UTC))
        .on_conflict_do_nothing(index_elements=["payment_intent_id"])
    )
    checkout = session.exec(select(CreditCheckout).where(
        col(CreditCheckout.payment_intent_id) == payment_intent_id
    )).first()
    if checkout is None:
        session.commit()
        return False
    claimed = session.execute(
        update(CreditCheckout)
        .where(CreditCheckout.stripe_session_id == checkout.stripe_session_id,
               CreditCheckout.reversed_at.is_(None))
        .values(reversed_at=datetime.now(UTC))
        .returning(CreditCheckout.stripe_session_id)
    ).scalar_one_or_none()
    if claimed is None:
        session.rollback()
        return False
    user = session.get(User, checkout.user_id)
    if user:
        user.status = UserStatus.SUSPENDED
        user.suspended_reason = "A credit payment was refunded or disputed. Contact support."
        session.add(user)
    session.add(CreditTransaction(
        user_id=checkout.user_id, amount=0,
        balance_after=balance(session, checkout.user_id),
        kind="payment_reversed", reference=f"stripe-reversed:{checkout.stripe_session_id}",
    ))
    session.commit()
    return True
