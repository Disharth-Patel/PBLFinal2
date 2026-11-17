"""Initial admissions schema."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("email", sa.String(255), nullable=False, unique=True), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("role", sa.String(20), nullable=False, server_default="student"), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("conversations", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("title", sa.String(200), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("messages", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False), sa.Column("role", sa.String(20), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("sources", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("leads", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("programme", sa.String(200)), sa.Column("academic_qualification", sa.String(200)), sa.Column("status", sa.String(40), nullable=False), sa.Column("interest_level", sa.String(40), nullable=False), sa.Column("notes", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("follow_ups", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id"), nullable=False), sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("due_at", sa.DateTime(), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("notes", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("audit_logs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("action", sa.String(100), nullable=False), sa.Column("resource", sa.String(100), nullable=False), sa.Column("detail", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))


def downgrade() -> None:
    for table in ("audit_logs", "follow_ups", "leads", "messages", "conversations", "users"):
        op.drop_table(table)
