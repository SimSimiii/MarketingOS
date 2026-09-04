"""Versioned verified deep-audience research.

Revision ID: e8a7c9d4f210
Revises: d1f83a5c62b7
Create Date: 2026-08-30 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "e8a7c9d4f210"
down_revision: str | Sequence[str] | None = "d1f83a5c62b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audienceresearchrow",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("audience_key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("audience_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("source_map_id", sa.Uuid(), nullable=True),
        sa.Column("source_map_version", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brand.id"]),
        sa.ForeignKeyConstraint(["source_map_id"], ["audiencemaprow.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audienceresearchrow_brand_id"),
        "audienceresearchrow",
        ["brand_id"],
    )
    op.create_index(
        op.f("ix_audienceresearchrow_audience_key"),
        "audienceresearchrow",
        ["audience_key"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_audienceresearchrow_audience_key"),
        table_name="audienceresearchrow",
    )
    op.drop_index(
        op.f("ix_audienceresearchrow_brand_id"),
        table_name="audienceresearchrow",
    )
    op.drop_table("audienceresearchrow")
