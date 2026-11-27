"""Add schedule, recurrence, and exchange fields to existing calendar item identities."""
from alembic import op
import sqlalchemy as sa

revision = "004_calendar"
down_revision = "003_shopping"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "calendar_events",
        sa.Column("item_id", sa.Text, sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("starts_at", sa.Text, nullable=False),
        sa.Column("ends_at", sa.Text, nullable=False),
        sa.Column("all_day", sa.Integer, nullable=False),
        sa.Column("recurrence_rule", sa.Text),
        sa.Column("exceptions", sa.Text, nullable=False, server_default="[]"),
        sa.Column("ics_uid", sa.Text),
        sa.CheckConstraint("all_day IN (0, 1)"),
    )
    op.create_index("calendar_household_uid", "calendar_events", ["household_id", "ics_uid"])
    op.get_bind().exec_driver_sql("INSERT INTO schema_migrations(version) VALUES (4)")
