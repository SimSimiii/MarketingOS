"""Give a campaign a channel, so it can deliver a LinkedIn message.

Revision ID: b1d7c9f4a20e
Revises: e8c4f6a25d03
"""
from alembic import op
import sqlalchemy as sa

revision = "b1d7c9f4a20e"
down_revision = "e8c4f6a25d03"
branch_labels = None
depends_on = None

#: The asset types after this revision. `linkedin_message` is the new one, and
#: at sixteen characters it is longer than every type the column was sized
#: for - SQLite would have stored it anyway and Postgres would have truncated
#: or refused it, which is the kind of difference that only shows up in
#: production. `alembic check` is what catches it here.
_ASSET_TYPE = sa.Enum(
    "EMAIL", "LINKEDIN_MESSAGE", "SOCIAL_POST", "AD", "BLOG", "LANDING_PAGE",
    name="assettype",
)


def upgrade() -> None:
    # A development database built by create_all already has the column; a
    # migrated one never does. Checked rather than assumed for the same reason
    # the LinkedIn table is: both shapes are supported and both reach here.
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("campaign")}
    if "channel" not in columns:
        op.add_column("campaign", sa.Column("channel", sa.JSON(), nullable=True))
    with op.batch_alter_table("generatedasset") as batch:
        batch.alter_column(
            "asset_type",
            existing_type=sa.String(length=12),
            type_=_ASSET_TYPE,
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("generatedasset") as batch:
        batch.alter_column(
            "asset_type",
            existing_type=_ASSET_TYPE,
            type_=sa.String(length=12),
            existing_nullable=False,
        )
    op.drop_column("campaign", "channel")
