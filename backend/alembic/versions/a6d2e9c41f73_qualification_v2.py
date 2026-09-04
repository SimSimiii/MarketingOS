"""Capability profiles, company qualification and campaign recommendation audit.

Revision ID: a6d2e9c41f73
Revises: f2c6b1a84d90
Create Date: 2026-09-01 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "a6d2e9c41f73"
down_revision: str | Sequence[str] | None = "f2c6b1a84d90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "productcapabilityprofilerow",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_version", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brand.id"]),
        sa.ForeignKeyConstraint(["knowledge_id"], ["knowledgeartifactset.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_productcapabilityprofilerow_brand_id"),
        "productcapabilityprofilerow",
        ["brand_id"],
    )
    op.create_index(
        op.f("ix_productcapabilityprofilerow_knowledge_id"),
        "productcapabilityprofilerow",
        ["knowledge_id"],
    )

    with op.batch_alter_table("prospectrow") as batch:
        batch.add_column(sa.Column("qualification", sa.JSON(), nullable=True))

    with op.batch_alter_table("relevancedossierrow") as batch:
        batch.add_column(sa.Column("capability_profile_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("capability_profile_version", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("qualification_fingerprint", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default="")
        )
        batch.add_column(sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"))
        batch.create_foreign_key(
            "fk_relevance_capability_profile",
            "productcapabilityprofilerow",
            ["capability_profile_id"],
            ["id"],
        )
        batch.create_index(
            op.f("ix_relevancedossierrow_capability_profile_id"),
            ["capability_profile_id"],
        )

    with op.batch_alter_table("campaign") as batch:
        batch.add_column(sa.Column("prospect_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_campaign_prospect", "prospectrow", ["prospect_id"], ["id"]
        )
        batch.create_index(op.f("ix_campaign_prospect_id"), ["prospect_id"])

    with op.batch_alter_table("campaignexecution") as batch:
        batch.add_column(sa.Column("recommendation_snapshot", sa.JSON(), nullable=True))
        batch.add_column(
            sa.Column(
                "generated_despite_recommendation",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("campaignexecution") as batch:
        batch.drop_column("generated_despite_recommendation")
        batch.drop_column("recommendation_snapshot")
    with op.batch_alter_table("campaign") as batch:
        batch.drop_index(op.f("ix_campaign_prospect_id"))
        batch.drop_constraint("fk_campaign_prospect", type_="foreignkey")
        batch.drop_column("prospect_id")
    with op.batch_alter_table("relevancedossierrow") as batch:
        batch.drop_index(op.f("ix_relevancedossierrow_capability_profile_id"))
        batch.drop_constraint("fk_relevance_capability_profile", type_="foreignkey")
        batch.drop_column("schema_version")
        batch.drop_column("qualification_fingerprint")
        batch.drop_column("capability_profile_version")
        batch.drop_column("capability_profile_id")
    with op.batch_alter_table("prospectrow") as batch:
        batch.drop_column("qualification")
    op.drop_index(
        op.f("ix_productcapabilityprofilerow_knowledge_id"),
        table_name="productcapabilityprofilerow",
    )
    op.drop_index(
        op.f("ix_productcapabilityprofilerow_brand_id"),
        table_name="productcapabilityprofilerow",
    )
    op.drop_table("productcapabilityprofilerow")
