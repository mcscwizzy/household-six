"""SQLAlchemy engine and additive, transactional SQLite upgrades."""
from functools import lru_cache
import os
from pathlib import Path
import sqlite3

from alembic import command, config
from sqlalchemy import URL, create_engine, event
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=8)
def engine(path):
    database = create_engine(
        URL.create("sqlite", database=str(path)), poolclass=NullPool,
        connect_args={"timeout": 10},
    )

    @event.listens_for(database, "connect")
    def configure(connection, _):
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        connection.execute("PRAGMA journal_mode=WAL")

    return database


def migrate(path):
    os.umask(0o077)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    settings = config.Config()
    settings.set_main_option("script_location", str(Path(__file__).with_name("db_migrations")))
    with engine(path).connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        settings.attributes["connection"] = connection
        command.upgrade(settings, "head")
        connection.commit()
    os.chmod(path, 0o600)


def apply_sql(connection, filename):
    """Replay the original migration and retain its original ledger entry."""
    version = int(filename.partition("_")[0])
    if connection.exec_driver_sql(
        "SELECT 1 FROM schema_migrations WHERE version=?", (version,),
    ).first():
        return
    pending = ""
    for line in (ROOT / "migrations" / filename).read_text(encoding="utf-8").splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            connection.exec_driver_sql(pending)
            pending = ""
    if pending.strip():
        raise ValueError("Incomplete migration statement")
    connection.exec_driver_sql("INSERT INTO schema_migrations(version) VALUES (?)", (version,))


class LegacyConnection:
    """Retain DB-API rows and errors for existing repositories on the shared engine."""
    def __init__(self, path):
        self.proxy = engine(path).raw_connection()
        self.driver = self.proxy.driver_connection

    def __getattr__(self, name):
        return getattr(self.driver, name)

    def close(self):
        self.proxy.close()

    def __enter__(self):
        return self

    def __exit__(self, *error):
        try:
            return self.driver.__exit__(*error)
        finally:
            self.close()
