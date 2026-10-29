"""Persist campaign intent without inventing facts for historical campaigns.

Revision ID: c53a9f27d401
Revises: b42e8d16c390
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c53a9f27d401"
down_revision: str | Sequence[str] | None = "b42e8d16c390"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("campaign", sa.Column("intent", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaign", "intent")
