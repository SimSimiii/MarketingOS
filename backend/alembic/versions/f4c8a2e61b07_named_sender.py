"""A named human sender for a campaign's emails.

Every email the system has ever produced is signed by a team, because the
writer was told it does not know who the sender is and the only honest
alternative to a name is the company. That is a real conversion cost paid for a
missing form field: a mail from a person who could be replied to and a mail
from "the growth team" are read as different kinds of object before either is
read as words.

Both columns are nullable and stay that way. A campaign without them behaves
exactly as it did - see `app.marketing.writer._sender`, where the absence has
its own instruction and the writer is forbidden from inventing a person to fill
the gap.

Revision ID: f4c8a2e61b07
Revises: e5b2c704da91
Create Date: 2026-08-13 16:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "f4c8a2e61b07"
down_revision: str | Sequence[str] | None = "e5b2c704da91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("campaign") as batch:
        batch.add_column(
            sa.Column("sender_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch.add_column(
            sa.Column("sender_role", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("campaign") as batch:
        batch.drop_column("sender_role")
        batch.drop_column("sender_name")
