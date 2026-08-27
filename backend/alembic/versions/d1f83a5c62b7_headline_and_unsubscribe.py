"""An unsubscribe link for the branded footer.

One nullable column on `brand`. Marketing mail is required to carry an
unsubscribe almost everywhere this will be sent, and the renderer draws the
line only when there is somewhere for it to go - a footer that says
"Unsubscribe" over a dead link is worse than one that does not mention it,
because the reader clicks, nothing happens, and the next thing they press is
the spam button.

The email's own headline and eyebrow need no migration: they live on the
`Email` model, which is copy rather than a row, and reach the database inside
`generatedasset.asset_metadata` like every other field of a finished email.

Revision ID: d1f83a5c62b7
Revises: c7a4e2b91d35
Create Date: 2026-08-27 11:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "d1f83a5c62b7"
down_revision: str | Sequence[str] | None = "c7a4e2b91d35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("brand") as batch:
        batch.add_column(
            sa.Column("unsubscribe_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("brand") as batch:
        batch.drop_column("unsubscribe_url")
