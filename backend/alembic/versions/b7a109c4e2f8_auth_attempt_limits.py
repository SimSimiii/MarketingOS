"""Shared password-attempt counters.

Revision ID: b7a109c4e2f8
Revises: a4e92f6b17c0
"""

import sqlalchemy as sa
from alembic import op

revision = "b7a109c4e2f8"
down_revision = "a4e92f6b17c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "authratelimit",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("window_start", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
    )
    op.create_index("ix_authratelimit_window_start", "authratelimit", ["window_start"])


def downgrade() -> None:
    op.drop_index("ix_authratelimit_window_start", table_name="authratelimit")
    op.drop_table("authratelimit")
