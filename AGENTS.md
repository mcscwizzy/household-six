# Household Six repository notes

- Keep household data local and do not add analytics or external identity dependencies.
- All reads and writes must include server-side household scoping. Treat the browser as untrusted.
- Validate request bodies, keep errors generic, and avoid logging identifiers or private content.
- Do not claim full feature parity or physical NAS/iPhone verification without evidence.
- The approved continuation architecture is Python + FastAPI/Uvicorn + SQLite/WAL + SQLAlchemy/Alembic, modular JavaScript, IndexedDB, SSE, and optional Ollama/MCP. See `docs/adr/0001-approved-runtime-and-data-store.md`.
- The current standard-library HTTP service is a temporary environment-driven compatibility baseline because package registry access is unavailable. Do not describe it as FastAPI or add PostgreSQL, Redis, hosted infrastructure, or another parallel architecture.
- Preserve alpha household IDs, users, password hashes, timestamps, assignments, and reward ledger records in additive, versioned migrations.
- Offline storage is default-deny for household data. Only member-keyed, minimal completion intents may be persisted; never infer the active identity from browser storage.
- Role checks, household scoping, expected versions, and idempotency must be enforced server-side.
- Run `python3 -m unittest discover -s tests -v` and `python3 -m compileall -q app tests scripts` after service changes.
