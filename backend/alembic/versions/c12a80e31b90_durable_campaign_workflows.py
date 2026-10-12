"""Durable campaign workflow admission, budgets and immutable inputs."""
import sqlalchemy as sa
from alembic import op

revision = "c12a80e31b90"
down_revision = "b7a109c4e2f8"
branch_labels = None
depends_on = None


def upgrade():
    for name in ("request_snapshot", "context_snapshot"):
        op.add_column("campaignrunstate", sa.Column(name, sa.JSON(), nullable=True))
    op.add_column("campaignrunstate", sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()))
    for name in ("model_calls", "model_tokens"):
        op.add_column("campaignrunstate", sa.Column(name, sa.Integer(), nullable=False, server_default="0"))
    op.add_column("campaignrunstate", sa.Column("deadline_at", sa.DateTime(), nullable=True))
    for name in ("inflight_step", "workflow_arn"):
        op.add_column("campaignrunstate", sa.Column(name, sa.String(), nullable=True))


def downgrade():
    for name in ("workflow_arn", "inflight_step", "deadline_at", "model_tokens", "model_calls", "cancel_requested", "context_snapshot", "request_snapshot"):
        op.drop_column("campaignrunstate", name)
