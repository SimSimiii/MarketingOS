"""True token accounting.

Every run before this migration recorded the uncached fraction of its input
and called it the input. With the Claude Code CLI that fraction is close to
zero - a call sending a 31,000-character system prompt reports `input_tokens:
2`, because the rest arrives as `cache_creation_input_tokens` and
`cache_read_input_tokens`, which nothing read. The consequences were not
cosmetic: `ExecutionPolicy.max_total_tokens` compared a real budget against a
number several times too small and could never fire, and the cost shown to the
user understated what their quota actually paid.

These columns are what make the numbers true. Existing rows keep their old
values and get 0 for the new ones - the information was never captured, so it
cannot be back-filled, and a historical row will read implausibly low beside a
recent one. That is the honest representation of what was recorded at the time.

Revision ID: d3a9f11c8b42
Revises: b7e2a94c1f38
Create Date: 2026-08-13 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3a9f11c8b42"
down_revision: str | Sequence[str] | None = "b7e2a94c1f38"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    NOT NULL with a server_default, so the rows already there get 0 rather
    than blocking the migration; SQLite needs batch mode to add them at all.
    """
    with op.batch_alter_table("agentexecution") as batch:
        batch.add_column(
            sa.Column(
                "cache_creation_input_tokens", sa.Integer(), nullable=False, server_default="0"
            )
        )
        batch.add_column(
            sa.Column(
                "cache_read_input_tokens", sa.Integer(), nullable=False, server_default="0"
            )
        )
        batch.add_column(
            sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0")
        )

    with op.batch_alter_table("campaignexecution") as batch:
        batch.add_column(
            sa.Column(
                "total_cache_read_tokens", sa.Integer(), nullable=False, server_default="0"
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("campaignexecution") as batch:
        batch.drop_column("total_cache_read_tokens")

    with op.batch_alter_table("agentexecution") as batch:
        batch.drop_column("cost_usd")
        batch.drop_column("cache_read_input_tokens")
        batch.drop_column("cache_creation_input_tokens")
