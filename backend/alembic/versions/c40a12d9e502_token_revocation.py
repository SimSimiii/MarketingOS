"""Immediate access-token revocation."""
import sqlalchemy as sa
from alembic import op

revision = "c40a12d9e502"
down_revision = "c40a12d9e501"
branch_labels = None
depends_on = None


def upgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("user")}
    if "token_version" not in columns:
        op.add_column("user", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))
        with op.batch_alter_table("user") as batch:
            batch.alter_column("token_version", server_default=None)


def downgrade():
    op.drop_column("user", "token_version")
