"""Add scoped, expiring credentials for private local MCP clients."""
from alembic import op
import sqlalchemy as sa

revision = "009_private_mcp"
down_revision = "008_calendar_timezone"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mcp_grants",
        sa.Column("token_hash", sa.Text, primary_key=True),
        sa.Column("id", sa.Text, nullable=False, unique=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.Text, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scopes", sa.Text, nullable=False),
        sa.Column("expires_at", sa.Text, nullable=False),
        sa.Column("revoked_at", sa.Text),
    )
    op.get_bind().exec_driver_sql("INSERT INTO schema_migrations(version) VALUES (9)")
