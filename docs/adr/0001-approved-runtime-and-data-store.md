# ADR 0001: Approved application runtime and data store

- **Status:** Accepted for continuation; implementation in progress
- **Date:** 2026-11-27

## Context

The initial alpha is a single-process Python 3.12 standard-library HTTP service using SQLite. The continuation requirements explicitly select Python, FastAPI/Uvicorn, SQLAlchemy/Alembic and SQLite, while keeping the core installable without AI, MCP, external identity or hosted services. Existing alpha data and the current household API must be preserved.

This environment has Python 3.12.3, Node 24.18.0 and npm 11.6.0, but no installed FastAPI, Uvicorn, SQLAlchemy, Alembic or MCP SDK. PyPI package resolution returned no versions from a temporary virtual environment, and npm registry DNS lookup failed. Creating a local listening socket is denied. Docker is installed, but the Compose plugin is absent and the daemon was not verified. Git reports `refs/remotes/origin/HEAD` as `origin/master`, but writing a feature ref is denied by the read-only `.git` metadata boundary.

## Decision

The target architecture is the user-approved lightweight modular monolith: maintained Python, FastAPI served by Uvicorn, SQLite in WAL mode, SQLAlchemy and Alembic, modular browser JavaScript, IndexedDB for narrowly scoped offline mutation intents, household-scoped SSE, optional local Ollama, optional Python MCP, and single-process Docker Compose deployment. No PostgreSQL, Redis, hosted identity, analytics, Kubernetes or second service architecture will be introduced.

Until dependencies can be installed and exercised, preserve the existing standard-library Python/SQLite service and its persisted data. Do not claim that it satisfies the selected FastAPI/SQLAlchemy/Alembic architecture. The current SQLite schema will gain an ordered migration ledger and additive migrations so the alpha remains runnable and migration work is not discarded. The adapter migration to SQLAlchemy/Alembic and FastAPI/Uvicorn remains blocked on dependency availability and HTTP socket testing.

The client stores no household record cache. IndexedDB is restricted to member-keyed completion intents containing an item ID, expected version, unique mutation ID and bounded retry metadata. These intents are available only after the same member authenticates online; a reload while offline is signed out. Browser storage is not encrypted and does not provide offline revocation guarantees.

## Consequences

- The alpha remains usable without third-party packages while its runtime is being migrated.
- New migrations are numbered, transactional and additive; migration tests preserve alpha IDs and records.
- The eventual dependency install path must run inside a virtual environment and use a committed lockfile produced in a registry-enabled environment.
- Compose, browser, physical iPhone and NAS behavior remain unverified here.
- Modules and integrations remain incomplete until each has working persistence, authorization, UI and executed tests.
