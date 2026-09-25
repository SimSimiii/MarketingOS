"""Widen knowledgedocument.source_type to every source the model accepts.

The initial schema created this column as a Postgres enum named
`knowledgesourcetype` with three members. The model has since become
`SourceType`, named `sourcetype`, with nine - PDF, DOCX, JSON and the media
kinds among them - and no migration ever followed. SQLite stores an enum as a
plain string, so nothing noticed; on Postgres every PDF or DOCX upload would
have been refused by the column's type. `alembic check` against a real
Postgres is what found it, the first time the chain ran there.

Postgres only. On SQLite the column is already a string wide enough for every
member, and `alembic check` there reports no difference.

Revision ID: 5b8e1d0c7a42
Revises: 2f7c2f4d9817
Create Date: 2026-09-25 19:40:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "5b8e1d0c7a42"
down_revision: Union[str, Sequence[str], None] = "2f7c2f4d9817"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW = sa.Enum(
    "WEBSITE", "MARKDOWN", "PLAIN_TEXT", "PDF", "DOCX", "JSON", "IMAGE", "VIDEO", "AUDIO",
    name="sourcetype",
)
_OLD = sa.Enum("MARKDOWN", "PLAIN_TEXT", "WEBSITE", name="knowledgesourcetype")


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    _NEW.create(bind, checkfirst=True)
    op.execute(
        "ALTER TABLE knowledgedocument ALTER COLUMN source_type "
        "TYPE sourcetype USING source_type::text::sourcetype"
    )
    _OLD.drop(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    # Rows holding a member the old type lacks (a PDF, say) cannot be
    # narrowed back; this fails loudly on them rather than guessing.
    _OLD.create(bind, checkfirst=True)
    op.execute(
        "ALTER TABLE knowledgedocument ALTER COLUMN source_type "
        "TYPE knowledgesourcetype USING source_type::text::knowledgesourcetype"
    )
    _NEW.drop(bind, checkfirst=True)
