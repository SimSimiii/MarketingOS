"""Preserve automatic proof source checks without certifying legacy quotes.

Revision ID: b42e8d16c390
Revises: a31f9e70c246
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b42e8d16c390"
down_revision: str | Sequence[str] | None = "a31f9e70c246"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("proofcandidaterow", sa.Column(
        "verification_status", sa.String(), nullable=False, server_default="not_checked",
    ))
    op.add_column("proofcandidaterow", sa.Column("context", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("proofcandidaterow", "context")
    op.drop_column("proofcandidaterow", "verification_status")
