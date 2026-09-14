"""Own standalone knowledge and backfill scoped documents without guessing owners."""
import sqlalchemy as sa
from alembic import op

revision = "c40a12d9e501"
down_revision = "b1d7c9f4a20e"
branch_labels = None
depends_on = None


def upgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("knowledgedocument")}
    if "owner_id" not in columns:
        with op.batch_alter_table("knowledgedocument") as batch:
            batch.add_column(sa.Column("owner_id", sa.Uuid(), nullable=True))
            batch.create_foreign_key("fk_knowledge_owner", "user", ["owner_id"], ["id"])
            batch.create_index("ix_knowledgedocument_owner_id", ["owner_id"])
    op.execute(sa.text('UPDATE knowledgedocument SET owner_id = '
                      '(SELECT owner_id FROM campaign WHERE campaign.id = knowledgedocument.campaign_id) '
                      'WHERE campaign_id IS NOT NULL AND owner_id IS NULL'))
    op.execute(sa.text('UPDATE knowledgedocument SET owner_id = '
                      '(SELECT owner_id FROM brand WHERE brand.id = knowledgedocument.brand_id) '
                      'WHERE campaign_id IS NULL AND brand_id IS NOT NULL AND owner_id IS NULL'))


def downgrade():
    with op.batch_alter_table("knowledgedocument") as batch:
        batch.drop_index("ix_knowledgedocument_owner_id")
        batch.drop_constraint("fk_knowledge_owner", type_="foreignkey")
        batch.drop_column("owner_id")
