"""Marketing-first schema.

Campaigns carry the user's request in their own words; knowledge is scoped to
a campaign so one product's material never leaks into another's copy; and a
single agent run can emit several ordered deliverables (a 3-email sequence
becomes three rows).

Existing rows get a placeholder `request` - there was no equivalent field
before, so it cannot be derived; edit those campaigns before re-running them.

Revision ID: 0d5fc427e579
Revises: c5fd057c72cb
Create Date: 2026-08-02 08:01:30.668946
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "0d5fc427e579"
down_revision: str | Sequence[str] | None = "c5fd057c72cb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LEGACY_REQUEST = "Produce the marketing material for this campaign."


def upgrade() -> None:
    """Upgrade schema.

    SQLite cannot ALTER columns in place, hence batch mode; NOT NULL columns
    need a server_default so existing rows remain valid.
    """
    with op.batch_alter_table("campaign") as batch:
        batch.add_column(
            sa.Column(
                "request",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=False,
                server_default=_LEGACY_REQUEST,
            )
        )
        batch.add_column(
            sa.Column("product_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )

    with op.batch_alter_table("generatedasset") as batch:
        batch.add_column(sa.Column("position", sa.Integer(), nullable=False, server_default="0"))
        batch.alter_column(
            "asset_type",
            existing_type=sa.VARCHAR(length=15),
            type_=sa.Enum("EMAIL", "SOCIAL_POST", "AD", "BLOG", "LANDING_PAGE", name="assettype"),
            existing_nullable=False,
        )

    with op.batch_alter_table("knowledgedocument") as batch:
        batch.add_column(sa.Column("campaign_id", sa.Uuid(), nullable=True))
        batch.add_column(
            sa.Column("word_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("document_metadata", sa.JSON(), nullable=True))
        batch.create_index(batch.f("ix_knowledgedocument_campaign_id"), ["campaign_id"])
        batch.create_foreign_key(
            "fk_knowledgedocument_campaign_id", "campaign", ["campaign_id"], ["id"]
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("knowledgedocument") as batch:
        batch.drop_constraint("fk_knowledgedocument_campaign_id", type_="foreignkey")
        batch.drop_index(batch.f("ix_knowledgedocument_campaign_id"))
        batch.drop_column("document_metadata")
        batch.drop_column("word_count")
        batch.drop_column("campaign_id")

    with op.batch_alter_table("generatedasset") as batch:
        batch.alter_column(
            "asset_type",
            existing_type=sa.Enum(
                "EMAIL", "SOCIAL_POST", "AD", "BLOG", "LANDING_PAGE", name="assettype"
            ),
            type_=sa.VARCHAR(length=15),
            existing_nullable=False,
        )
        batch.drop_column("position")

    with op.batch_alter_table("campaign") as batch:
        batch.drop_column("product_url")
        batch.drop_column("request")
