# Backup and restore

Create timestamped snapshots in the persistent backup volume with `docker compose run --rm household-six python3 /app/scripts/backup.py`. Schedule it with DSM Task Scheduler. Export those files to a second protected NAS share with `docker compose cp household-six:/app/backups /volume1/household-six-backups` while the main service is running. A Docker volume survives app-container replacement, but a second copy is still needed for NAS failure.

The script uses SQLite's online backup API, then archives the snapshot. Verify an archive periodically by restoring to a new empty data volume: stop the app, set `DATA_PATH=household-six-restore-data`, run `docker compose run --rm household-six python3 /app/scripts/restore.py /app/backups/<archive>.tar.gz`, verify the restored DB, update `.env` with that `DATA_PATH`, then start the app. The script checks the archive's single expected member and runs `PRAGMA integrity_check`; it refuses to overwrite an existing database.

No uploaded files exist in this alpha, so the database is the current data set. When media storage is added, database and file snapshots must be coordinated. Backups contain password hashes and personal family records; encrypt and restrict them.
