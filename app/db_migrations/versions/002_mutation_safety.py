"""Preserve session security and idempotent mutation receipts."""
from alembic import op

from app.database import apply_sql

revision = "002_mutation_safety"
down_revision = "001_alpha"
branch_labels = None
depends_on = None


def upgrade():
    apply_sql(op.get_bind(), "002_session_and_mutation_safety.sql")
