"""Persist user email analyses.

Revision ID: a31f9e70c246
Revises: d91c382aa410
"""
from alembic import op
import sqlalchemy as sa

revision = "a31f9e70c246"
down_revision = "d91c382aa410"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("emailanalysis"):
        return
    op.create_table(
        "emailanalysis",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brand.id"), nullable=False),
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
    op.create_index("ix_emailanalysis_brand_id", "emailanalysis", ["brand_id"])


def downgrade() -> None:
    op.drop_index("ix_emailanalysis_brand_id", table_name="emailanalysis")
    op.drop_table("emailanalysis")
