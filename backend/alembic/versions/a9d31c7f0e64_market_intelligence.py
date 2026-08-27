"""Market intelligence: competitors, scans, found proof and the radar feed.

Four new tables and nothing touched. Everything the system knew before this
was something one company said about itself; these hold the half that can only
come from outside it - who else the buyer is deciding between, what each of
them promises, who has vouched for this company anywhere on the open web, and
what has moved since the last time anybody looked.

They are separate tables rather than one payload because they have different
owners and different lifetimes. `rival` is edited by the user and must survive
every rescan. `marketscan` is versioned and never overwritten, because the
radar's whole product is the difference between two of them. `proofcandidaterow`
outlives every recompile, since an approval cost a human a decision and a new
pricing page must not throw it away. `radareventrow` is kept rather than
recomputed, because the snapshots it was derived from may since have been
superseded.

Every table is brand-scoped. A market belongs to the business, not to one
campaign, which is the same reason compiled knowledge does.

Revision ID: a9d31c7f0e64
Revises: f4c8a2e61b07
Create Date: 2026-08-26 11:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "a9d31c7f0e64"
down_revision: str | Sequence[str] | None = "f4c8a2e61b07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "rival",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("kind", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("why", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("added_by", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("muted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brand.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rival_brand_id"), "rival", ["brand_id"])

    op.create_table(
        "marketscan",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("rivals_profiled", sa.Integer(), nullable=False),
        sa.Column("claims_verified", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brand.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_marketscan_brand_id"), "marketscan", ["brand_id"])

    op.create_table(
        "proofcandidaterow",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("claim", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("verbatim", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("attributed_to", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("venue", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("caveat", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("evidence_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("found_at", sa.DateTime(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["brand_id"], ["brand.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_proofcandidaterow_brand_id"), "proofcandidaterow", ["brand_id"]
    )
    op.create_index(op.f("ix_proofcandidaterow_status"), "proofcandidaterow", ["status"])

    op.create_table(
        "radareventrow",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("headline", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("detail", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("severity", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("rival", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("axis", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("what_to_do", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("seen_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["brand_id"], ["brand.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_radareventrow_brand_id"), "radareventrow", ["brand_id"])
    op.create_index(op.f("ix_radareventrow_severity"), "radareventrow", ["severity"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_radareventrow_severity"), table_name="radareventrow")
    op.drop_index(op.f("ix_radareventrow_brand_id"), table_name="radareventrow")
    op.drop_table("radareventrow")
    op.drop_index(op.f("ix_proofcandidaterow_status"), table_name="proofcandidaterow")
    op.drop_index(op.f("ix_proofcandidaterow_brand_id"), table_name="proofcandidaterow")
    op.drop_table("proofcandidaterow")
    op.drop_index(op.f("ix_marketscan_brand_id"), table_name="marketscan")
    op.drop_table("marketscan")
    op.drop_index(op.f("ix_rival_brand_id"), table_name="rival")
    op.drop_table("rival")
