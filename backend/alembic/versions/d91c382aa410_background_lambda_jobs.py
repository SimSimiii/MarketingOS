"""Durable market and knowledge jobs for asynchronous Lambda."""
import sqlalchemy as sa
from alembic import op

revision = "d91c382aa410"
down_revision = "c12a80e31b90"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("backgroundjob",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brand.id"), nullable=False),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("status", sa.JSON(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("claimed", sa.Boolean(), nullable=False),
        sa.Column("model_calls", sa.Integer(), nullable=False),
        sa.Column("model_tokens", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_backgroundjob_brand_id", "backgroundjob", ["brand_id"])
    op.create_index("ix_backgroundjob_owner_id", "backgroundjob", ["owner_id"])


def downgrade():
    op.drop_table("backgroundjob")
