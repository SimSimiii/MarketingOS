"""HTML email rendering.

A campaign's deliverable was plain text and nothing else, shown to the user in
a `<pre>`. The email it describes is already fully structured - subject,
preview, greeting, body, CTA, sign-off and P.S. are separate typed fields on
`Email` - so what was missing was never a representation, only a renderer.

`generatedasset.content_html` holds the rendered version. `content` stays the
canonical deliverable: it is what a text-only client shows, what the spam
filters like to see beside an HTML part, and what the user pastes when they
want to paste text. Rows written before this migration keep NULL and render
as text, which is what they always were.

The three columns on `brand` are the entire visual identity the renderer
takes. Everything about them is optional, and an email for a brand with none
of them set still renders in the typographic tier - which for cold outreach is
the better default anyway.

Revision ID: e5b2c704da91
Revises: d3a9f11c8b42
Create Date: 2026-08-13 12:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "e5b2c704da91"
down_revision: str | Sequence[str] | None = "d3a9f11c8b42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("generatedasset") as batch:
        batch.add_column(
            sa.Column("content_html", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )

    with op.batch_alter_table("brand") as batch:
        batch.add_column(
            sa.Column("logo_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch.add_column(
            sa.Column("primary_color", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch.add_column(sa.Column("footer_lines", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("brand") as batch:
        batch.drop_column("footer_lines")
        batch.drop_column("primary_color")
        batch.drop_column("logo_url")

    with op.batch_alter_table("generatedasset") as batch:
        batch.drop_column("content_html")
