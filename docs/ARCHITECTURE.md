# Architecture

## Approved target

Household Six is a single-process, local-first modular monolith. The approved continuation stack is Python 3.12+, FastAPI and Uvicorn, SQLite in WAL mode, SQLAlchemy, Alembic, modular JavaScript, IndexedDB for minimal offline mutation intents, and household-scoped Server-Sent Events. Ollama and the Python MCP SDK are optional and disabled by default. Docker Compose is the NAS deployment boundary. The core must run without AI, MCP, internet access or external identity.

The project does not use PostgreSQL, Redis, Kubernetes, hosted infrastructure or a separate parallel application architecture. Never put the active SQLite database on SMB or NFS storage.

## Current implementation

The repository still runs the original dependency-free `app/server.py` service with `sqlite3` and `ThreadingHTTPServer`. Registry access prevented installing or validating the approved runtime packages. This baseline remains in place to preserve the runnable alpha and household data; it is not FastAPI/Uvicorn or SQLAlchemy/Alembic feature parity.

`migrations/001_initial.sql` describes the alpha schema. `migrations/002_session_and_mutation_safety.sql` is additive and adds disabled-account state plus durable mutation receipts. `schema_migrations` records successfully applied numbered SQL files in a transaction. Migration testing checks that alpha records remain present. A real production data directory has not been migrated in this environment.

## Data and trust boundaries

- SQLite is authoritative. Every query and mutation must be scoped by the authenticated household on the server.
- The browser is untrusted. Offline storage holds no household records. IndexedDB may hold only a member-keyed task completion intent with expected version, unique mutation ID and bounded retry metadata.
- Offline intents are never loaded before the same member authenticates online. Offline reload is signed out. Browser storage is not encrypted and client state cannot guarantee revocation while disconnected.
- HTTP, UI, AI, MCP and jobs must call the same application services once the modular service layer is established.
- SSE is currently process-local and has no durable replay. Keep deployment single-process until shared event delivery is implemented.

## Current request flow

```mermaid
sequenceDiagram
  participant M as Household member
  participant B as Browser PWA
  participant S as Current Python service
  participant D as SQLite WAL
  M->>B: Complete an eligible task
  B->>S: POST with session, CSRF, expected version and mutation ID
  S->>D: Scope by household; check role and version in a short write transaction
  D-->>S: Commit result and unique mutation receipt
  S-->>B: 200, or typed 401/403/404/409/422 response
  B-->>M: Confirm, revert or reconcile state
```

## Modularization target

Split the current monolith into `app/config.py`, `app/database/`, `app/auth/`, `app/api/`, `app/models/`, `app/schemas/`, `app/services/`, `app/integrations/`, `app/ai/`, `app/mcp/`, `app/jobs/`, and `app/static/{components,modules,styles,icons}`. This layout is not yet implemented; avoid claiming otherwise. Preserve the current user IDs, password hashes, timestamps, assignments and points ledger during the adapter migration.
