"""Add structured recipes, weekly meal slots, and grocery synchronization."""
from alembic import op
import sqlalchemy as sa

revision = "006_meals"
down_revision = "005_chores_rewards"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "recipes",
        sa.Column("id", sa.Text, sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("servings", sa.Integer, nullable=False),
        sa.Column("instructions", sa.Text, nullable=False),
    )
    op.create_table(
        "recipe_ingredients",
        sa.Column("recipe_id", sa.Text, sa.ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("position", sa.Integer, primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("quantity", sa.Text, nullable=False),
        sa.Column("unit", sa.Text, nullable=False),
        sa.Column("category", sa.Text, nullable=False),
    )
    op.create_table(
        "meal_slots",
        sa.Column("id", sa.Text, sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day", sa.Text, nullable=False),
        sa.Column("slot", sa.Text, nullable=False),
        sa.Column("recipe_id", sa.Text, sa.ForeignKey("recipes.id")),
        sa.Column("servings", sa.Integer, nullable=False),
        sa.CheckConstraint("slot IN ('breakfast','lunch','dinner','snack')"),
    )
    op.create_index("meal_week", "meal_slots", ["household_id", "day"])
    op.create_table(
        "grocery_sources",
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("list_key", sa.Text, primary_key=True),
        sa.Column("week_start", sa.Text, primary_key=True),
        sa.Column("ingredient_key", sa.Text, primary_key=True),
        sa.Column("item_id", sa.Text, sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
    )
    op.get_bind().exec_driver_sql("INSERT INTO schema_migrations(version) VALUES (6)")
