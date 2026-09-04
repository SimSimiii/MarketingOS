"""Versioned relevance dossiers over exact intelligence triples.

Revision ID: f2c6b1a84d90
Revises: e8a7c9d4f210
Create Date: 2026-08-31 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "f2c6b1a84d90"
down_revision: str | Sequence[str] | None = "e8a7c9d4f210"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "relevancedossierrow",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("audience_key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("audience_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("audience_research_id", sa.Uuid(), nullable=False),
        sa.Column("audience_research_version", sa.Integer(), nullable=False),
        sa.Column("knowledge_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_version", sa.Integer(), nullable=False),
        sa.Column("market_scan_id", sa.Uuid(), nullable=False),
        sa.Column("market_scan_version", sa.Integer(), nullable=False),
        sa.Column("generation_version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["audience_research_id"], ["audienceresearchrow.id"]),
        sa.ForeignKeyConstraint(["brand_id"], ["brand.id"]),
        sa.ForeignKeyConstraint(["knowledge_id"], ["knowledgeartifactset.id"]),
        sa.ForeignKeyConstraint(["market_scan_id"], ["marketscan.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "audience_key",
        "audience_research_id",
        "brand_id",
        "knowledge_id",
        "market_scan_id",
    ):
        op.create_index(
            op.f(f"ix_relevancedossierrow_{column}"),
            "relevancedossierrow",
            [column],
        )


def downgrade() -> None:
    for column in (
        "market_scan_id",
        "knowledge_id",
        "brand_id",
        "audience_research_id",
        "audience_key",
    ):
        op.drop_index(
            op.f(f"ix_relevancedossierrow_{column}"),
            table_name="relevancedossierrow",
        )
    op.drop_table("relevancedossierrow")
