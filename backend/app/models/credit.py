"""Prepaid customer credits and the immutable movements behind the balance."""

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Field, SQLModel


class CreditAccount(SQLModel, table=True):
    user_id: UUID = Field(primary_key=True, foreign_key="user.id")
    balance: int = Field(default=0, ge=0)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CreditTransaction(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    amount: int
    balance_after: int
    kind: str
    reference: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CreditCheckout(SQLModel, table=True):
    stripe_session_id: str = Field(primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    credits: int
    amount_cents: int
    currency: str = "usd"
    livemode: bool = False
    payment_intent_id: str | None = Field(default=None, index=True, unique=True)
    credited_at: datetime | None = None
    reversed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReversedStripePayment(SQLModel, table=True):
    payment_intent_id: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
