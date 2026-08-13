"""Structured execution events.

An execution log line stops being only a sentence: it now carries which agent
emitted it, which director step it belongs to, what kind of event it was, the
exact payload broadcast over SSE, and its position in that stream. That is
what lets the UI show a per-agent log lane, and lets a page that reloaded
mid-run replay the timeline and resume the stream without a gap.

Existing rows keep their message and get NULL for the new descriptive
columns - they predate the structure, so it cannot be derived. They render as
plain "log" entries.

Revision ID: a1c7e4b93f20
Revises: 0d5fc427e579
Create Date: 2026-08-04 10:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "a1c7e4b93f20"
down_revision: str | Sequence[str] | None = "0d5fc427e579"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    SQLite cannot ALTER columns in place, hence batch mode; `sequence` is NOT
    NULL so it needs a server_default for the rows already there.
    """
    with op.batch_alter_table("executionlog") as batch:
        batch.add_column(sa.Column("agent_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
        batch.add_column(sa.Column("step", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("event_type", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch.add_column(sa.Column("data", sa.JSON(), nullable=True))
        batch.add_column(
            sa.Column("sequence", sa.Integer(), nullable=False, server_default="0")
        )
        batch.create_index(batch.f("ix_executionlog_agent_id"), ["agent_id"])
        batch.create_index(batch.f("ix_executionlog_event_type"), ["event_type"])
        # The live view reads one run's lines in the order they happened, on
        # every page load and every reconnect - the one query that must not
        # degrade as the log table grows.
        batch.create_index(batch.f("ix_executionlog_created_at"), ["created_at"])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("executionlog") as batch:
        batch.drop_index(batch.f("ix_executionlog_created_at"))
        batch.drop_index(batch.f("ix_executionlog_event_type"))
        batch.drop_index(batch.f("ix_executionlog_agent_id"))
        batch.drop_column("sequence")
        batch.drop_column("data")
        batch.drop_column("event_type")
        batch.drop_column("step")
        batch.drop_column("agent_id")
