# Database

The alpha uses SQLite in WAL mode at `$DATA_DIR/household.sqlite3`. `migrations/001_initial.sql` contains idempotent table and index creation. Tables include households, users, sessions, generic household list items, a points ledger, and an audit log. Foreign keys are enabled on every connection; completion runs inside `BEGIN IMMEDIATE` and a unique ledger constraint prevents repeat awards.

This does not meet the requested PostgreSQL/Drizzle migration and RLS design. Keep database files on persistent storage. Do not manually edit the DB while the service is running. To move to PostgreSQL, define a real migration history, preserve IDs and household keys, and verify isolation and ledger consistency before switching.
