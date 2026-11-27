# Upgrades

1. Read release notes and back up the persistent data directory.
2. Pull/copy the reviewed application source and rebuild with `docker compose build`.
3. Recreate with `docker compose up -d` and confirm `/api/health` and application sign-in.
4. Keep the preceding image and backup until data integrity is confirmed.

The current schema initializer uses idempotent `CREATE TABLE IF NOT EXISTS`; there is not yet an ordered migration runner or downgrade tool. Do not assume a future schema change is reversible. Restore a verified backup into a separate path for rollback rather than replacing an active database.
