"""Add household shopping lists and versioned item metadata."""
from alembic import op
import sqlalchemy as sa

revision = "003_shopping"
down_revision = "002_mutation_safety"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "shopping_lists",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(collation="NOCASE"), nullable=False),
        sa.Column("created_at", sa.Text, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("household_id", "name"),
    )
    op.execute("ALTER TABLE items ADD COLUMN shopping_list_id TEXT REFERENCES shopping_lists(id)")
    op.add_column("items", sa.Column("quantity", sa.Text, nullable=False, server_default=""))
    op.add_column("items", sa.Column("category", sa.Text, nullable=False, server_default=""))
    op.add_column("items", sa.Column("deleted_at", sa.Text))
    op.add_column("mutation_receipts", sa.Column("request_hash", sa.Text))
    op.create_index("shopping_by_list", "items", ["household_id", "shopping_list_id", "kind", "completed"])
    op.get_bind().exec_driver_sql("INSERT INTO schema_migrations(version) VALUES (3)")
