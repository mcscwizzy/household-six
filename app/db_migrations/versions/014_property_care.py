"""Add household-scoped property and vehicle service records."""
from alembic import op
import sqlalchemy as sa

revision = "014_property_care"
down_revision = "013_account_administration"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "maintenance_assets",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("category", sa.Text, nullable=False),
        sa.Column("location", sa.Text, nullable=False, server_default=""),
        sa.Column("instructions", sa.Text, nullable=False, server_default=""),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
        sa.Column("created_by", sa.Text, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.Text, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("archived_at", sa.Text),
    )
    op.create_index("maintenance_assets_by_household", "maintenance_assets", ["household_id", "archived_at", "title"])
    op.create_table(
        "maintenance_schedules",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", sa.Text, sa.ForeignKey("maintenance_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("frequency", sa.Text, nullable=False),
        sa.Column("interval_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("due_on", sa.Text, nullable=False),
        sa.Column("season", sa.Text, nullable=False, server_default=""),
        sa.Column("assigned_to", sa.Text, sa.ForeignKey("users.id")),
        sa.Column("estimated_cost_cents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("active", sa.Integer, nullable=False, server_default="1"),
        sa.CheckConstraint("frequency IN ('once','daily','weekly','monthly','quarterly','yearly')"),
        sa.CheckConstraint("interval_count BETWEEN 1 AND 120"),
        sa.CheckConstraint("estimated_cost_cents BETWEEN 0 AND 1000000000"),
    )
    op.create_index("maintenance_due", "maintenance_schedules", ["household_id", "active", "due_on"])
    op.create_table(
        "maintenance_history",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("mutation_id", sa.Text, nullable=False),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("schedule_id", sa.Text, sa.ForeignKey("maintenance_schedules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", sa.Text, sa.ForeignKey("maintenance_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("performed_by", sa.Text, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("performed_on", sa.Text, nullable=False),
        sa.Column("cost_cents", sa.Integer, nullable=False),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.Text, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("cost_cents BETWEEN 0 AND 1000000000"),
    )
    op.create_index("maintenance_history_mutation_unique", "maintenance_history", ["household_id", "mutation_id"], unique=True)
    op.create_index("maintenance_history_by_schedule", "maintenance_history", ["household_id", "schedule_id", "performed_on"])
    op.create_table(
        "vehicles",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("make", sa.Text, nullable=False),
        sa.Column("model", sa.Text, nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("vin", sa.Text, nullable=False, server_default=""),
        sa.Column("fuel", sa.Text, nullable=False),
        sa.Column("nickname", sa.Text, nullable=False, server_default=""),
        sa.Column("odometer", sa.Integer, nullable=False, server_default="0"),
        sa.Column("registration_due", sa.Text),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("archived_at", sa.Text),
        sa.CheckConstraint("fuel IN ('gasoline','diesel','hybrid','electric')"),
        sa.CheckConstraint("year BETWEEN 1886 AND 2200"),
        sa.CheckConstraint("odometer BETWEEN 0 AND 2000000"),
    )
    op.create_index("vehicles_by_household", "vehicles", ["household_id", "archived_at", "make", "model"])
    op.create_table(
        "vehicle_services",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("household_id", sa.Text, sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vehicle_id", sa.Text, sa.ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_type", sa.Text, nullable=False),
        sa.Column("performed_on", sa.Text, nullable=False),
        sa.Column("odometer", sa.Integer, nullable=False),
        sa.Column("due_on", sa.Text),
        sa.Column("due_odometer", sa.Integer),
        sa.Column("interval_months", sa.Integer),
        sa.Column("interval_miles", sa.Integer),
        sa.Column("cost_cents", sa.Integer, nullable=False),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.Text, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("odometer BETWEEN 0 AND 2000000"),
        sa.CheckConstraint("cost_cents BETWEEN 0 AND 1000000000"),
    )
    op.create_index("vehicle_service_history", "vehicle_services", ["household_id", "vehicle_id", "performed_on"])
    op.get_bind().exec_driver_sql("INSERT INTO schema_migrations(version) VALUES (14)")
