"""Additive profile and device-session fields for household account management."""
import uuid

from alembic import op
import sqlalchemy as sa

revision = "013_account_administration"
down_revision = "012_habits_allowance"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("avatar_key", sa.Text, nullable=False, server_default="person"))
    op.add_column("users", sa.Column("managed_profile", sa.Integer, nullable=False, server_default="0"))
    op.add_column("sessions", sa.Column("device_name", sa.Text, nullable=False, server_default="Household device"))
    op.add_column("sessions", sa.Column("device_id", sa.Text))
    connection = op.get_bind()
    for (session_hash,) in connection.exec_driver_sql("SELECT id_hash FROM sessions"):
        connection.exec_driver_sql("UPDATE sessions SET device_id=? WHERE id_hash=?",
                                   (str(uuid.uuid4()), session_hash))
    op.create_index("sessions_device_id_unique", "sessions", ["device_id"], unique=True)
    op.add_column("households", sa.Column("parent_pin_hash", sa.Text))
    op.get_bind().exec_driver_sql("INSERT INTO schema_migrations(version) VALUES (13)")
