#!/usr/bin/env python3
"""Restore a validated archive. Stop the application before running."""
import os
import sqlite3
import sys
import tarfile
import tempfile
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit("Usage: python3 scripts/restore.py backups/household-six-<timestamp>.tar.gz")
target = Path(os.environ.get("DATA_DIR", "./data")) / "household.sqlite3"
archive = Path(sys.argv[1])
if not archive.is_file() or not tarfile.is_tarfile(archive):
    raise SystemExit("Backup archive was not found or is not a tar archive")
with tempfile.TemporaryDirectory() as tmp:
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        if len(members) != 1 or members[0].name != "household.sqlite3" or not members[0].isfile():
            raise SystemExit("Archive must contain only household.sqlite3")
        tar.extractall(tmp, filter="data")
    candidate = Path(tmp) / "household.sqlite3"
    with sqlite3.connect(candidate) as con:
        result = con.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise SystemExit(f"Backup integrity check failed: {result}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise SystemExit(f"Refusing to overwrite {target}. Move it aside after taking a backup, then retry.")
    target.write_bytes(candidate.read_bytes())
    os.chmod(target, 0o600)
print(f"Restored {archive} to {target}")
