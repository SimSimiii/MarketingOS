"""Revoke operator access tokens after logout and password reset."""
import sqlalchemy as sa
from alembic import op

revision = "c40a12d9e503"
down_revision = "c40a12d9e502"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("adminuser") as batch:
        batch.add_column(sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))
    with op.batch_alter_table("adminuser") as batch:
        batch.alter_column("token_version", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("adminuser") as batch:
        batch.drop_column("token_version")
