"""Accounts, sessions, and the back-office.

Four new tables and three new keys. The keys are the interesting part: `brand`
and `campaign` get an `owner_id`, and those two columns are the whole of
multi-tenancy (see app.auth.scope) because every other table in the schema
hangs off one of them.

Both are nullable, deliberately. An existing database has rows that predate
accounts, and there is no user to attribute them to at migration time -
inventing one would silently hand somebody's work to an account they never
created. They stay unowned until `scripts/claim_workspace.py` adopts them, and
until then only single-user mode can see them.

Every step is guarded, for the same reason `c4f19d2a8e60` is: `init_db()` runs
`SQLModel.metadata.create_all` on startup, so anyone who started the server
before running this already has the four tables - empty, and indistinguishable
from the ones below. An unguarded `create_table` would fail on "table already
exists" and leave the database half-migrated, which is a worse place to be
than either end of the migration.

Revision ID: d7b3e5f14c92
Revises: c4f19d2a8e60
Create Date: 2026-09-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "d7b3e5f14c92"
down_revision: str | Sequence[str] | None = "c4f19d2a8e60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


#: (constraint name, table, column). Named rather than left to Alembic,
#: because batch mode on SQLite cannot drop an anonymous constraint later.
_OWNER_FOREIGN_KEYS = [
    ("fk_brand_owner_id_user", "brand", "owner_id"),
    ("fk_campaign_owner_id_user", "campaign", "owner_id"),
    ("fk_usersettings_user_id_user", "usersettings", "user_id"),
]


# ── What the database already has ───────────────────────────────────────────
#
# Re-inspected per call rather than cached once: this migration creates the
# very objects it asks about, so a snapshot taken at the top would be stale by
# the third question.


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return name in _inspector().get_table_names()


def _has_column(table: str, column: str) -> bool:
    return column in {c["name"] for c in _inspector().get_columns(table)}


def _has_index(table: str, name: str) -> bool:
    return name in {i["name"] for i in _inspector().get_indexes(table)}


def _has_foreign_key(table: str, column: str) -> bool:
    """Whether `table.column` already points at something.

    Matched on the column rather than on the constraint name: a table built by
    `create_all` carries the key SQLModel declared, and SQLite gives that one
    no name at all - so a name comparison would miss it and batch mode would
    add a second, identical key.
    """
    return any(
        column in key.get("constrained_columns", [])
        for key in _inspector().get_foreign_keys(table)
    )


def _index(name: str, table: str, columns: list[str], *, unique: bool = False) -> None:
    if not _has_index(table, name):
        op.create_index(name, table, columns, unique=unique)


def _column(table: str, column: sa.Column) -> None:
    if not _has_column(table, column.name):
        op.add_column(table, column)


def upgrade() -> None:
    if not _has_table("user"):
        op.create_table(
            "user",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("password_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("full_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("company_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("role", sa.Enum("OWNER", "MEMBER", name="userrole"), nullable=False),
            sa.Column(
                "status",
                sa.Enum("ACTIVE", "PENDING", "SUSPENDED", name="userstatus"),
                nullable=False,
            ),
            sa.Column(
                "plan", sa.Enum("FREE", "PRO", "BUSINESS", name="userplan"), nullable=False
            ),
            sa.Column("suspended_reason", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("monthly_run_quota", sa.Integer(), nullable=False),
            sa.Column("runs_used", sa.Integer(), nullable=False),
            sa.Column("quota_reset_at", sa.DateTime(), nullable=True),
            sa.Column("email_verified_at", sa.DateTime(), nullable=True),
            sa.Column("last_login_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    # Unique rather than merely indexed: the address is the login, and two rows
    # sharing one is an ambiguous sign-in rather than a duplicate record.
    _index("ix_user_email", "user", ["email"], unique=True)
    _index("ix_user_plan", "user", ["plan"])
    _index("ix_user_status", "user", ["status"])

    if not _has_table("usersession"):
        op.create_table(
            "usersession",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("token_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("user_agent", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("ip_address", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _index("ix_usersession_token_hash", "usersession", ["token_hash"], unique=True)
    _index("ix_usersession_user_id", "usersession", ["user_id"])

    if not _has_table("adminuser"):
        op.create_table(
            "adminuser",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("password_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("full_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column(
                "role",
                sa.Enum("SUPPORT", "ADMIN", "SUPERADMIN", name="adminrole"),
                nullable=False,
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("last_login_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    _index("ix_adminuser_email", "adminuser", ["email"], unique=True)

    if not _has_table("adminauditlog"):
        op.create_table(
            "adminauditlog",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("admin_id", sa.Uuid(), nullable=True),
            sa.Column("admin_email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("action", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("target_type", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("target_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("detail", sa.JSON(), nullable=True),
            sa.Column("ip_address", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["admin_id"], ["adminuser.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _index("ix_adminauditlog_action", "adminauditlog", ["action"])
    _index("ix_adminauditlog_admin_id", "adminauditlog", ["admin_id"])
    _index("ix_adminauditlog_created_at", "adminauditlog", ["created_at"])

    # The two columns that are the whole of multi-tenancy, plus the
    # per-account settings key. `create_all` never adds a column to a table it
    # already made, so these are precisely what an existing database lacks -
    # and the reason it fails with "no such column: campaign.owner_id" rather
    # than with anything about migrations.
    _column("brand", sa.Column("owner_id", sa.Uuid(), nullable=True))
    _index("ix_brand_owner_id", "brand", ["owner_id"])
    _column("campaign", sa.Column("owner_id", sa.Uuid(), nullable=True))
    _index("ix_campaign_owner_id", "campaign", ["owner_id"])
    _column("usersettings", sa.Column("user_id", sa.Uuid(), nullable=True))
    _index("ix_usersettings_user_id", "usersettings", ["user_id"], unique=True)

    # SQLite has no ALTER TABLE ADD CONSTRAINT, so the foreign key goes on
    # through batch mode, which rebuilds the table around it. Worth the rewrite
    # rather than skipping the constraint on SQLite: an identical schema on
    # both engines is what lets `alembic check` stay a usable invariant, and a
    # divergence tolerated once is a divergence nobody notices growing.
    for constraint, table, column in _OWNER_FOREIGN_KEYS:
        if _has_foreign_key(table, column):
            continue
        with op.batch_alter_table(table) as batch:
            batch.create_foreign_key(constraint, "user", [column], ["id"])


def downgrade() -> None:
    for constraint, table, _ in reversed(_OWNER_FOREIGN_KEYS):
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(constraint, type_="foreignkey")

    op.drop_index("ix_usersettings_user_id", table_name="usersettings")
    op.drop_column("usersettings", "user_id")
    op.drop_index("ix_campaign_owner_id", table_name="campaign")
    op.drop_column("campaign", "owner_id")
    op.drop_index("ix_brand_owner_id", table_name="brand")
    op.drop_column("brand", "owner_id")

    op.drop_index("ix_adminauditlog_created_at", table_name="adminauditlog")
    op.drop_index("ix_adminauditlog_admin_id", table_name="adminauditlog")
    op.drop_index("ix_adminauditlog_action", table_name="adminauditlog")
    op.drop_table("adminauditlog")
    op.drop_index("ix_adminuser_email", table_name="adminuser")
    op.drop_table("adminuser")
    op.drop_index("ix_usersession_user_id", table_name="usersession")
    op.drop_index("ix_usersession_token_hash", table_name="usersession")
    op.drop_table("usersession")
    op.drop_index("ix_user_status", table_name="user")
    op.drop_index("ix_user_plan", table_name="user")
    op.drop_index("ix_user_email", table_name="user")
    op.drop_table("user")
