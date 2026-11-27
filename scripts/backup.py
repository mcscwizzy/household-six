#!/usr/bin/env python3
"""Create a consistent SQLite snapshot in a timestamped archive."""
import os
import sqlite3
import tarfile
from datetime import datetime, timezone
from pathlib import Path

os.umask(0o077)
data = Path(os.environ.get("DATA_DIR", "./data"))
db = data / "household.sqlite3"
out = Path(os.environ.get("BACKUP_DIR", "./backups"))
if not db.exists():
    raise SystemExit(f"Database not found at {db}")
out.mkdir(parents=True, exist_ok=True)
os.chmod(out, 0o700)
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
snapshot = out / f"household-six-{stamp}.sqlite3"
with sqlite3.connect(db) as source, sqlite3.connect(snapshot) as target:
    source.backup(target)
archive = out / f"household-six-{stamp}.tar.gz"
with tarfile.open(archive, "w:gz") as tar:
    tar.add(snapshot, arcname="household.sqlite3")
snapshot.unlink()
os.chmod(archive, 0o600)
print(f"Created {archive}")
