"""Add announcement visibility metadata and member acknowledgments."""
from alembic import op
import sqlalchemy as sa

revision = "011_announcements"
down_revision = "010_inventory"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "announcement_settings",
        sa.Column("id", sa.Text, sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pinned", sa.Integer, nullable=False, server_default="0"),
        sa.Column("expires_on", sa.Text),
        sa.CheckConstraint("pinned IN (0,1)"),
    )
    op.create_table(
        "announcement_reads",
        sa.Column("announcement_id", sa.Text, sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("member_id", sa.Text, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("read_version", sa.Integer, nullable=False),
        sa.Column("read_at", sa.Text, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.get_bind().exec_driver_sql("INSERT INTO schema_migrations(version) VALUES (11)")
