"""Create the alpha schema, or adopt the existing alpha database."""
from alembic import op

from app.database import apply_sql

revision = "001_alpha"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    connection.exec_driver_sql(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    apply_sql(connection, "001_initial.sql")
