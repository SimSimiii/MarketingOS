"""Persist LinkedIn searches and message drafts.

Revision ID: e8c4f6a25d03
Revises: d7b3e5f14c92
"""
from alembic import op
import sqlalchemy as sa

revision = "e8c4f6a25d03"
down_revision = "d7b3e5f14c92"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("linkedinrun"):
        return
    op.create_table(
        "linkedinrun",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brand.id"), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("active_key", sa.String(), nullable=True, unique=True),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("error", sa.String(), nullable=False),
        sa.Column("calls", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_linkedinrun_brand_id", "linkedinrun", ["brand_id"])


def downgrade() -> None:
    op.drop_index("ix_linkedinrun_brand_id", table_name="linkedinrun")
    op.drop_table("linkedinrun")
