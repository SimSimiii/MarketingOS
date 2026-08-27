"""Where a campaign's call to action points.

One nullable column. The writer is told, correctly, that it does not know the
URL behind any button - inventing one sends a real reader to a page that does
not exist - so it writes the words that go on the link and the link has to
come from somewhere else. This is that somewhere.

Without it the branded tier could only ever render a button with `href="#"`,
which is worse than the plain tier's underlined link: a reader who clicks a
button and lands nowhere has learned something about the sender that no amount
of copy recovers. The renderer now falls back to the link when there is no
URL, so this column is what makes the button reachable at all.

Nullable and no default, because most campaigns will not set it and the
brand's own website is a good enough fallback for those that do not.

Revision ID: c7a4e2b91d35
Revises: b6e1f9c4d70a
Create Date: 2026-08-27 09:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "c7a4e2b91d35"
down_revision: str | Sequence[str] | None = "b6e1f9c4d70a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("campaign") as batch:
        batch.add_column(
            sa.Column("cta_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("campaign") as batch:
        batch.drop_column("cta_url")
