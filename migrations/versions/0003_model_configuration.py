"""Model configuration table."""

from alembic import op
import sqlalchemy as sa

revision = "0003_model_configuration"
down_revision = "0002_student_experience"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_configurations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_name", sa.String(200), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.2"),
        sa.Column("top_p", sa.Float(), nullable=False, server_default="0.9"),
        sa.Column("context_length", sa.Integer(), nullable=False, server_default="4096"),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="512"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("model_configurations")
