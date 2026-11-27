"""Keep source timezones for imported timed recurring events."""
from alembic import op
import sqlalchemy as sa

revision = "008_calendar_timezone"
down_revision = "007_six"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("calendar_events", sa.Column("event_timezone", sa.Text))
    op.get_bind().exec_driver_sql("INSERT INTO schema_migrations(version) VALUES (8)")
