"""Persist chore schedules, completion review, and reward redemptions."""
from alembic import op
import sqlalchemy as sa

revision = "005_chores_rewards"
down_revision = "004_calendar"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "chores",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("details", sa.Text, nullable=False),
        sa.Column("start_date", sa.Text, nullable=False),
        sa.Column("repeat", sa.Text, nullable=False),
        sa.Column("routine", sa.Text, nullable=False),
        sa.Column("points", sa.Integer, nullable=False),
        sa.Column("requires_approval", sa.Integer, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_by", sa.Text, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("archived_at", sa.Text),
        sa.CheckConstraint("repeat IN ('once','daily','weekly')"),
        sa.CheckConstraint("routine IN ('anytime','morning','bedtime')"),
        sa.CheckConstraint("points BETWEEN 0 AND 10000 AND requires_approval IN (0,1)"),
    )
    op.create_index("chores_by_household", "chores", ["household_id", "archived_at"])
    op.create_table(
        "chore_assignments",
        sa.Column("chore_id", sa.Text, sa.ForeignKey("chores.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("member_id", sa.Text, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
    )
    op.create_table(
        "chore_completions",
        sa.Column("id", sa.Text, sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("chore_id", sa.Text, sa.ForeignKey("chores.id"), nullable=False),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("due_date", sa.Text, nullable=False),
        sa.Column("beneficiary", sa.Text, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("checked_by", sa.Text, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("submitted_at", sa.Text, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("reviewed_at", sa.Text),
        sa.CheckConstraint("status IN ('pending','approved','declined')"),
    )
    op.create_index("chore_history", "chore_completions", ["household_id", "status", "due_date"])
    op.create_table(
        "reward_redemptions",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reward_id", sa.Text, sa.ForeignKey("items.id"), nullable=False),
        sa.Column("member_id", sa.Text, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("cost", sa.Integer, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("requested_at", sa.Text, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("reviewed_at", sa.Text),
        sa.CheckConstraint("status IN ('pending','approved','declined')"),
    )
    op.create_index("reward_queue", "reward_redemptions", ["household_id", "status", "requested_at"])
    op.get_bind().exec_driver_sql("INSERT INTO schema_migrations(version) VALUES (5)")
