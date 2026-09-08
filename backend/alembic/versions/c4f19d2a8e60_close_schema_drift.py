"""Close the drift between the models and the migration chain.

None of these columns are new work. They have been on the SQLModel classes for
a while and have only ever existed in a database because `init_db()` runs
`SQLModel.metadata.create_all` on startup - so a developer's SQLite file has
them and a database built the supported way, `alembic upgrade head`, does not.

That never showed up locally, and it is fatal the first time the schema is
built by migration alone: token accounting, campaign policy and the archive
flag would all be missing, and the first run against that database would fail
on the first INSERT.

Every column is added with a `server_default` so it can land on a table that
already has rows, and the defaults match what the model would have written.

Revision ID: c4f19d2a8e60
Revises: b1e7d3f95a24
Create Date: 2026-09-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "c4f19d2a8e60"
down_revision: str | Sequence[str] | None = "b1e7d3f95a24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    """What the live database actually has.

    A developer's file was built by `create_all` and already carries most of
    this; a freshly migrated database carries none of it. The same migration
    has to be right for both, so each column is added only where it is missing
    rather than assumed either way.
    """
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table)}


def _indexes(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {index["name"] for index in inspector.get_indexes(table)}


#: (table, column, type, server default) - the default is what the model's own
#: default would have produced for a row written before the column existed.
_MISSING_COLUMNS = [
    ("agentexecution", "model", sqlmodel.sql.sqltypes.AutoString(), None),
    ("agentexecution", "input_tokens", sa.Integer(), "0"),
    ("agentexecution", "output_tokens", sa.Integer(), "0"),
    ("agentexecution", "duration_ms", sa.Float(), "0"),
    ("agentexecution", "attempt", sa.Integer(), "1"),
    ("campaign", "archived_at", sa.DateTime(), None),
    ("campaign", "policy", sa.JSON(), None),
    ("campaign", "model_overrides", sa.JSON(), None),
    ("campaignexecution", "total_input_tokens", sa.Integer(), "0"),
    ("campaignexecution", "total_output_tokens", sa.Integer(), "0"),
    ("campaignexecution", "estimated_cost_usd", sa.Float(), "0"),
]

_MISSING_INDEXES = [
    ("ix_campaign_status", "campaign", ["status"]),
    ("ix_campaignexecution_status", "campaignexecution", ["status"]),
]


def upgrade() -> None:
    for table, column, column_type, default in _MISSING_COLUMNS:
        if column in _columns(table):
            continue
        op.add_column(
            table,
            sa.Column(column, column_type, nullable=default is None, server_default=default),
        )

    # `status` is the one enum in the set. SQLAlchemy stores a Python enum by
    # member *name*, so the stored value is "ACTIVE" rather than "active" -
    # writing the value here would produce rows the ORM cannot load back.
    if "status" not in _columns("campaign"):
        op.add_column(
            "campaign",
            sa.Column(
                "status",
                sa.Enum("ACTIVE", "ARCHIVED", name="campaignstatus"),
                nullable=False,
                server_default="ACTIVE",
            ),
        )

    for name, table, columns in _MISSING_INDEXES:
        if name not in _indexes(table):
            op.create_index(name, table, columns, unique=False)


def downgrade() -> None:
    for name, table, _ in _MISSING_INDEXES:
        if name in _indexes(table):
            op.drop_index(name, table_name=table)
    if "status" in _columns("campaign"):
        op.drop_column("campaign", "status")
    for table, column, _, _default in reversed(_MISSING_COLUMNS):
        if column in _columns(table):
            op.drop_column(table, column)
