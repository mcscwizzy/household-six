# Database

## Current alpha

The running alpha uses SQLite in WAL mode at `$DATA_DIR/household.sqlite3`. Foreign keys are enabled for each connection, writes use short transactions, task points have a uniqueness constraint, and item queries are scoped by household ID. The current alpha schema still contains a generic `items` table and is not the normalized product schema.

Numbered SQL files under `migrations/` are applied in order and recorded in `schema_migrations`. Each migration and its version insert run in one `BEGIN IMMEDIATE` transaction. Migration 001 represents the alpha schema. Migration 002 adds disabled-account state and household/member-bound mutation receipts without replacing alpha records.

The migration test reruns upgrades over a disposable alpha-shaped database and verifies an existing task remains. No production household DB was available for a live upgrade. Back up the active database before upgrades, keep it local to the NAS's local filesystem, and never place the active SQLite database on SMB/NFS.

## Approved target

The target persists dedicated domain entities through SQLAlchemy on the same local SQLite database and uses Alembic revisions for schema changes. FastAPI routes, background work, AI and MCP must call shared application services. That adapter and model conversion are not implemented yet. Preserve user IDs, password hashes, timestamps, assignments, existing item IDs and points-ledger history during any normalization.
