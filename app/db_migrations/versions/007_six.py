"""Persist bounded local assistant jobs and confirmation proposals."""
from alembic import op
import sqlalchemy as sa

revision = "007_six"
down_revision = "006_meals"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assistant_jobs",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.Text, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("state", sa.Text, nullable=False),
        sa.Column("payload", sa.Text),
        sa.Column("result", sa.Text),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.Text, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expires_at", sa.Text, nullable=False),
    )
    op.create_index("assistant_queue", "assistant_jobs", ["state", "created_at"])
    op.create_index("assistant_member_jobs", "assistant_jobs", ["household_id", "actor_id", "created_at"])
    op.get_bind().exec_driver_sql("INSERT INTO schema_migrations(version) VALUES (7)")
