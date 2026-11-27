# Upgrades and rollback

1. Stop writes or schedule a quiet period; create and protect a current backup.
2. Preserve a copy of the previous image and database path.
3. Review ordered migration files. The alpha migrator applies unapplied numbered SQL files transactionally and records their versions in `schema_migrations`.
4. On a disposable local database, run `python3 -m unittest discover -s tests -v` and `python3 -m compileall -q app tests scripts` before upgrading the household copy.
5. Start the new application, check `/api/health`, then verify sign-in, household lists and point ledger data.
6. Keep the previous database and backup until the updated data has been validated.

Migration 002 adds a `disabled_at` column and mutation-receipt table. The migration test preserves alpha records in a disposable database. This environment had no production household DB to upgrade, so back up before using it. For rollback, stop the app and restore a verified backup into a new empty data directory; do not reverse-edit or overwrite the active copy. Coordinate uploaded files with database backups once file storage exists.

Alembic adopts the existing numbered SQL ledger and applies later additive migrations inside a SQLite write transaction. The app performs this upgrade at startup.
