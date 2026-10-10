"""Prepaid credit balance, transaction history and Stripe checkout records.

Revision ID: a4e92f6b17c0
Revises: 5b8e1d0c7a42
"""

import sqlalchemy as sa
from alembic import op

revision = "a4e92f6b17c0"
down_revision = "5b8e1d0c7a42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "creditaccount",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id"), primary_key=True),
        sa.Column("balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("balance >= 0", name="ck_creditaccount_nonnegative"),
    )
    op.create_table(
        "credittransaction",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("reference", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_credittransaction_user_id", "credittransaction", ["user_id"])
    op.create_index("ix_credittransaction_reference", "credittransaction", ["reference"], unique=True)
    op.create_table(
        "creditcheckout",
        sa.Column("stripe_session_id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("livemode", sa.Boolean(), nullable=False),
        sa.Column("payment_intent_id", sa.String(), nullable=True),
        sa.Column("credited_at", sa.DateTime(), nullable=True),
        sa.Column("reversed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_creditcheckout_user_id", "creditcheckout", ["user_id"])
    op.create_index("ix_creditcheckout_payment_intent_id", "creditcheckout", ["payment_intent_id"], unique=True)
    op.create_table(
        "reversedstripepayment",
        sa.Column("payment_intent_id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("reversedstripepayment")
    op.drop_index("ix_creditcheckout_payment_intent_id", table_name="creditcheckout")
    op.drop_index("ix_creditcheckout_user_id", table_name="creditcheckout")
    op.drop_table("creditcheckout")
    op.drop_index("ix_credittransaction_reference", table_name="credittransaction")
    op.drop_index("ix_credittransaction_user_id", table_name="credittransaction")
    op.drop_table("credittransaction")
    op.drop_table("creditaccount")
