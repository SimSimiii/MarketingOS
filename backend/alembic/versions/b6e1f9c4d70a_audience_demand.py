"""The demand side: mapped audiences, named prospects, and the segment a campaign chose.

Two new tables and one new column, and the split is the same one the market
tables already make. `audiencemaprow` is a compiled reading of who would buy
this, versioned and never overwritten, because the useful question next month
is which segments appeared and which fell away. `prospectrow` is rows, because
the user works on them: they dismiss the one that is obviously too large and
keep the eleven they will write to, and those decisions have to survive the
next search.

`campaign.audience_segment` is what connects the two halves. It holds the name
of a segment from the brand's map, and it is a name rather than a foreign key
on purpose - segments live inside a versioned payload, so an id would be a
reference into a document that the next remap replaces, and a campaign would
silently lose the audience it was written for.

Nullable with no default, because it is genuinely optional: a campaign that
names no segment is written to the audience the company's own material
describes, which is what every campaign before this migration did.

Revision ID: b6e1f9c4d70a
Revises: a9d31c7f0e64
Create Date: 2026-08-26 14:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "b6e1f9c4d70a"
down_revision: str | Sequence[str] | None = "a9d31c7f0e64"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "audiencemaprow",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("segments", sa.Integer(), nullable=False),
        sa.Column("unobvious_segments", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brand.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audiencemaprow_brand_id"), "audiencemaprow", ["brand_id"])

    op.create_table(
        "prospectrow",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("segment", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("what_they_do", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("why_them", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("verbatim", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("fit", sa.Float(), nullable=False),
        sa.Column("contacts", sa.JSON(), nullable=True),
        sa.Column("caveat", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("pages_read", sa.Integer(), nullable=False),
        sa.Column("invented_contacts", sa.Integer(), nullable=False),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("found_at", sa.DateTime(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["brand_id"], ["brand.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_prospectrow_brand_id"), "prospectrow", ["brand_id"])
    op.create_index(op.f("ix_prospectrow_segment"), "prospectrow", ["segment"])
    op.create_index(op.f("ix_prospectrow_status"), "prospectrow", ["status"])

    with op.batch_alter_table("campaign") as batch:
        batch.add_column(
            sa.Column(
                "audience_segment", sqlmodel.sql.sqltypes.AutoString(), nullable=True
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("campaign") as batch:
        batch.drop_column("audience_segment")

    op.drop_index(op.f("ix_prospectrow_status"), table_name="prospectrow")
    op.drop_index(op.f("ix_prospectrow_segment"), table_name="prospectrow")
    op.drop_index(op.f("ix_prospectrow_brand_id"), table_name="prospectrow")
    op.drop_table("prospectrow")
    op.drop_index(op.f("ix_audiencemaprow_brand_id"), table_name="audiencemaprow")
    op.drop_table("audiencemaprow")
