"""Add pantry, refrigerator, and freezer stock without replacing alpha items."""
from alembic import op
import sqlalchemy as sa

revision = "010_inventory"
down_revision = "009_private_mcp"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inventory_stock",
        sa.Column("id", sa.Text, sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("location", sa.Text, nullable=False),
        sa.Column("quantity", sa.Text, nullable=False),
        sa.Column("unit", sa.Text, nullable=False),
        sa.Column("threshold", sa.Text, nullable=False),
        sa.Column("expires_on", sa.Text),
        sa.CheckConstraint("location IN ('pantry','refrigerator','freezer')"),
    )
    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.Text, sa.ForeignKey("inventory_stock.id"), nullable=False),
        sa.Column("actor_id", sa.Text, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("direction", sa.Text, nullable=False),
        sa.Column("amount", sa.Text, nullable=False),
        sa.Column("unit", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("direction IN ('use','restock')"),
    )
    op.create_index("stock_history", "stock_movements", ["household_id", "created_at"])
    op.get_bind().exec_driver_sql("INSERT INTO schema_migrations(version) VALUES (10)")
