"""Audiences the user described by hand.

Revision ID: b1e7d3f95a24
Revises: a6d2e9c41f73
Create Date: 2026-09-06 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "b1e7d3f95a24"
down_revision: str | Sequence[str] | None = "a6d2e9c41f73"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "useraudiencerow",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("audience_key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brand.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_useraudiencerow_brand_id"),
        "useraudiencerow",
        ["brand_id"],
    )
    op.create_index(
        op.f("ix_useraudiencerow_audience_key"),
        "useraudiencerow",
        ["audience_key"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_useraudiencerow_audience_key"),
        table_name="useraudiencerow",
    )
    op.drop_index(
        op.f("ix_useraudiencerow_brand_id"),
        table_name="useraudiencerow",
    )
    op.drop_table("useraudiencerow")
