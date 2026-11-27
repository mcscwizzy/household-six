# Architecture

## Approved target

Household Six is a single-process, local-first modular monolith. The approved continuation stack is Python 3.12+, FastAPI and Uvicorn, SQLite in WAL mode, SQLAlchemy, Alembic, modular JavaScript, IndexedDB for minimal offline mutation intents, and household-scoped Server-Sent Events. Ollama and the Python MCP SDK are optional and disabled by default. Docker Compose is the NAS deployment boundary. The core must run without AI, MCP, internet access or external identity.

The project does not use PostgreSQL, Redis, Kubernetes, hosted infrastructure or a separate parallel application architecture. Never put the active SQLite database on SMB or NFS storage.

## Current implementation

FastAPI serves the UI and API through Uvicorn. SQLAlchemy provides configured SQLite connections and domain queries. Alembic adopts the existing alpha migration ledger and applies additive migrations in a single SQLite write transaction. The legacy item and authentication queries retain SQLite DB-API behavior on the same engine.

The application boundary is a single local SQLite file in WAL mode. Repository migrations preserve alpha IDs, timestamps, memberships, hashes, assignments and ledger entries. The upgrade tests run on synthetic alpha records.

## Data and trust boundaries

- SQLite is authoritative. Every query and mutation must be scoped by the authenticated household on the server.
- The browser is untrusted. Offline storage holds no household records. IndexedDB may hold only a member-keyed completion intent with expected version, unique mutation ID and bounded retry metadata.
- Offline intents are never loaded before the same member authenticates online. Offline reload is signed out. Browser storage is not encrypted and client state cannot guarantee revocation while disconnected.
- HTTP, UI, AI, MCP and jobs must call the same application services for equivalent authorization and business rules.
- SSE is currently process-local and has no durable replay. Keep deployment single-process until shared event delivery is implemented.

## Current request flow

```mermaid
sequenceDiagram
  participant M as Household member
  participant B as Browser PWA
  participant S as FastAPI
  participant D as SQLite WAL
  M->>B: Complete an eligible task
  B->>S: POST with session, CSRF, expected version and mutation ID
  S->>D: Scope by household; check role and version in a short write transaction
  D-->>S: Commit result and unique mutation receipt
  S-->>B: 200, or typed 401/403/404/409/422 response
  B-->>M: Confirm, revert or reconcile state
```

## Modules

`app/server.py` owns HTTP routing, response security and the original session API. Separate Python modules own calendar, chores, rewards, meals, shopping, inventory, announcements, assistant jobs and MCP. Browser modules in `app/static` render those domains. `app/database.py` configures SQLite, and `app/db_migrations` contains the Alembic revisions.
