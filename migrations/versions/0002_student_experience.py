"""Student profile, feedback and escalation tables."""

from alembic import op
import sqlalchemy as sa

revision = "0002_student_experience"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("phone", sa.String(40), nullable=False, server_default=""),
        sa.Column("academic_qualification", sa.String(200), nullable=False, server_default=""),
        sa.Column("interested_programme", sa.String(200), nullable=False, server_default=""),
        sa.Column("preferred_department", sa.String(200), nullable=False, server_default=""),
        sa.Column("admission_year", sa.String(20), nullable=False, server_default=""),
        sa.Column("communication_language", sa.String(40), nullable=False, server_default="English"),
        sa.Column("interests", sa.Text(), nullable=False, server_default=""),
    )
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("messages.id")),
        sa.Column("rating", sa.String(20), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "escalations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id")),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="Pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    for table in ("escalations", "feedback", "student_profiles"):
        op.drop_table(table)
