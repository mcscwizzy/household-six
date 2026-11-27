# ADR 0001: Approved application runtime and data store

- **Status:** Accepted for continuation; implementation in progress
- **Date:** 2026-11-27

## Context

The initial alpha is a single-process Python 3.12 standard-library HTTP service using SQLite. The continuation requirements explicitly select Python, FastAPI/Uvicorn, SQLAlchemy/Alembic and SQLite, while keeping the core installable without AI, MCP, external identity or hosted services. Existing alpha data and the current household API must be preserved.

## Decision

The target architecture is the user-approved lightweight modular monolith: maintained Python, FastAPI served by Uvicorn, SQLite in WAL mode, SQLAlchemy and Alembic, modular browser JavaScript, IndexedDB for narrowly scoped offline mutation intents, household-scoped SSE, optional local Ollama, optional Python MCP, and single-process Docker Compose deployment. No PostgreSQL, Redis, hosted identity, analytics, Kubernetes or second service architecture will be introduced.

The application uses Uvicorn to serve FastAPI. SQLAlchemy owns SQLite connection configuration and Alembic applies the schema with an explicit SQLite write transaction. The migration revisions adopt existing entries in `schema_migrations` so upgrades preserve the prior ledger and alpha data. Existing domain SQL keeps the SQLite DB-API row and transaction behavior over the shared engine.

The client stores no household record cache. IndexedDB is restricted to member-keyed completion intents containing an item ID, expected version, unique mutation ID and bounded retry metadata. These intents are available only after the same member authenticates online; a reload while offline is signed out. Browser storage is not encrypted and does not provide offline revocation guarantees.

## Consequences

- New migrations are numbered, transactional and additive; migration tests preserve alpha IDs and records.
- The runtime installs into a Python 3.12 virtual environment or container from the committed, hash-checked lockfile.
- Physical iPhone and NAS behavior require device verification.
- Modules and integrations remain incomplete until each has working persistence, authorization, UI and executed tests.
