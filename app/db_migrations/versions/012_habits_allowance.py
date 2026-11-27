"""Add private household-local habit tracking and an immutable allowance ledger."""
from alembic import op
import sqlalchemy as sa

revision = "012_habits_allowance"
down_revision = "011_announcements"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "habits",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_id", sa.Text, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("details", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("archived_at", sa.Text),
    )
    op.create_index("habits_by_member", "habits", ["household_id", "member_id", "archived_at"])
    op.create_table(
        "habit_checkins",
        sa.Column("habit_id", sa.Text, sa.ForeignKey("habits.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("day", sa.Text, primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.Text, sa.ForeignKey("users.id"), nullable=False),
    )
    op.create_table(
        "allowance_entries",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_id", sa.Text, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("actor_id", sa.Text, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount_cents", sa.Integer, nullable=False),
        sa.Column("note", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("amount_cents<>0"),
    )
    op.create_index("allowance_by_member", "allowance_entries", ["household_id", "member_id", "created_at"])
    op.get_bind().exec_driver_sql("INSERT INTO schema_migrations(version) VALUES (12)")
