"""Brand-scoped knowledge and compiled artifact sets.

Knowledge stops belonging to a campaign and starts belonging to the business.
A company's pricing page is the same page it was during their last campaign,
so compiling it once and reusing it is the difference between a second
campaign starting from everything the first one learned and starting from an
empty page.

Two new tables and two new columns:
  * `brand` - the business a campaign is for. Optional: a campaign without one
    keeps its knowledge to itself, which is right for a one-off.
  * `knowledgeartifactset` - one compiled version of what we know about a
    business, keyed by a fingerprint of the material that produced it so an
    unchanged corpus is never recompiled. Versions are kept, not overwritten,
    so a campaign's copy stays explainable after the company edits its site.
  * `campaign.brand_id` / `knowledgedocument.brand_id` - both nullable, so
    every existing campaign and document keeps working exactly as before,
    scoped to itself.

Nothing is dropped and nothing is rewritten: the redesign that replaced the
director with a code pipeline changed no existing table.

Revision ID: b7e2a94c1f38
Revises: a1c7e4b93f20
Create Date: 2026-08-05 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "b7e2a94c1f38"
down_revision: str | Sequence[str] | None = "a1c7e4b93f20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "brand",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("website_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "knowledgeartifactset",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=True),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source_fingerprint", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brand.id"]),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledgeartifactset_brand_id"), "knowledgeartifactset", ["brand_id"]
    )
    op.create_index(
        op.f("ix_knowledgeartifactset_campaign_id"), "knowledgeartifactset", ["campaign_id"]
    )
    # Looking up "have we already compiled exactly this material?" happens once
    # per run, before anything else - it must not table-scan.
    op.create_index(
        op.f("ix_knowledgeartifactset_source_fingerprint"),
        "knowledgeartifactset",
        ["source_fingerprint"],
    )

    # SQLite cannot add a column with a foreign key in place, hence batch mode.
    with op.batch_alter_table("campaign") as batch:
        batch.add_column(sa.Column("brand_id", sa.Uuid(), nullable=True))
        batch.create_index(batch.f("ix_campaign_brand_id"), ["brand_id"])
        batch.create_foreign_key("fk_campaign_brand_id", "brand", ["brand_id"], ["id"])

    with op.batch_alter_table("knowledgedocument") as batch:
        batch.add_column(sa.Column("brand_id", sa.Uuid(), nullable=True))
        batch.create_index(batch.f("ix_knowledgedocument_brand_id"), ["brand_id"])
        batch.create_foreign_key("fk_knowledgedocument_brand_id", "brand", ["brand_id"], ["id"])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("knowledgedocument") as batch:
        batch.drop_constraint("fk_knowledgedocument_brand_id", type_="foreignkey")
        batch.drop_index(batch.f("ix_knowledgedocument_brand_id"))
        batch.drop_column("brand_id")

    with op.batch_alter_table("campaign") as batch:
        batch.drop_constraint("fk_campaign_brand_id", type_="foreignkey")
        batch.drop_index(batch.f("ix_campaign_brand_id"))
        batch.drop_column("brand_id")

    op.drop_index(
        op.f("ix_knowledgeartifactset_source_fingerprint"), table_name="knowledgeartifactset"
    )
    op.drop_index(op.f("ix_knowledgeartifactset_campaign_id"), table_name="knowledgeartifactset")
    op.drop_index(op.f("ix_knowledgeartifactset_brand_id"), table_name="knowledgeartifactset")
    op.drop_table("knowledgeartifactset")
    op.drop_table("brand")
