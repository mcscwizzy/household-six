# Household Six repository notes

- Keep household data local and do not add analytics or external identity dependencies.
- All reads and writes must include server-side household scoping. Treat the browser as untrusted.
- Validate request bodies, keep errors generic, and avoid logging identifiers or private content.
- Do not claim full feature parity or physical NAS/iPhone verification without evidence.
- The approved continuation architecture is Python + FastAPI/Uvicorn + SQLite/WAL + SQLAlchemy/Alembic, modular JavaScript, IndexedDB, SSE, and optional Ollama/MCP. See `docs/adr/0001-approved-runtime-and-data-store.md`.
- FastAPI/Uvicorn is the web runtime. Keep SQLite on local storage and avoid PostgreSQL, Redis, hosted infrastructure, or another parallel architecture.
- Preserve alpha household IDs, users, password hashes, timestamps, assignments, and reward ledger records in additive, versioned migrations.
- Offline storage is default-deny for household data. Only member-keyed, minimal completion intents may be persisted; never infer the active identity from browser storage.
- Role checks, household scoping, expected versions, and idempotency must be enforced server-side.
- Run `python3 -m unittest discover -s tests -v` and `python3 -m compileall -q app tests scripts` after service changes.

## Current continuation facts

- The current branch adds additive database migrations through version 14. Preserve the original household identifiers and all existing user, password, timestamp, assignment, mutation receipt and reward ledger data.
- Account administration currently supports profile name/color/avatar edits, disable/reactivate, administrator-assisted password reset, self session management and owner/administrator member-session listing and revocation. Invitations, parent PINs, managed child profiles and shared-device profile switching remain unfinished.
- Home maintenance and vehicle service records are local, adult-managed modules. Templates are inert until explicitly saved. Upcoming due dates appear in Today for adult roles. Uploaded supporting documents and general reminder delivery are not yet available.
- Browser smoke coverage is `npm run test:e2e`; the local suite exercises Chromium and WebKit at common phone, tablet and desktop widths. Physical iPhone, iPad and NAS acceptance must be reported separately.
- Keep feature and security documentation explicit about partial work. Do not describe the branch as Household Six v1.0 or as production-ready until the full acceptance checklist is met.
