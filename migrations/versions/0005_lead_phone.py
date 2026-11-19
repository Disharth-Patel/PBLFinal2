"""Add contact phone to admission leads."""

from alembic import op
import sqlalchemy as sa

revision = "0005_lead_phone"
down_revision = "0004_knowledge_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("phone", sa.String(length=40), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("leads") as batch_op:
        batch_op.drop_column("phone")
