# Household Six Implementation Plan

> **Superseded historical plan:** This initial proposal selected Next.js/PostgreSQL. The active continuation architecture is Python/FastAPI/SQLite/SQLAlchemy/Alembic under the user's later request; see [ADR 0001](../../adr/0001-approved-runtime-and-data-store.md), [active requirements](../../REQUIREMENTS.md), and [current implementation status](../../../IMPLEMENTATION_STATUS.md). Tasks below are historical and are not evidence of delivered features.

> **For agentic workers:** Implement the application task-by-task, preserving the project scope and tracking gaps.

**Goal:** Ship a self-hostable, authenticated family organizer with real persistence, usable responsive PWA surfaces, and deployment documentation.

**Architecture:** A Next.js modular monolith serves the PWA and authenticated JSON API. PostgreSQL stores household-scoped records and sessions; shared services enforce access and idempotency. Optional worker, Caddy, Ollama, and MCP services remain isolated.

**Tech Stack:** Next.js App Router, strict TypeScript, PostgreSQL, Drizzle ORM, Zod, Tailwind, PWA service worker, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-11-27-household-six-design.md`

## Global Constraints

- Self-hosted, LAN-first, and functional without cloud services or AI.
- Enforce household membership and permissions on every server mutation.
- Persist real application data; never seed outside explicit development mode.
- Do not cache authentication or sensitive files in the PWA shell.
- Make AI, MCP, Caddy, and external integrations opt-in.

## Review Focus

- Cross-household identifiers must not permit reading or writing another household's records; exercise service authorization.
- Repeated/offline task completion must not award duplicate points; exercise idempotency.
- Missing owner, wrong password, and expired session must fail closed.
- Daylight-saving transitions must not silently shift recurring local events.
- Offline or unavailable server must not imply a mutation was synchronized.

### Task 1: Project and deployment foundation

- [ ] Add package scripts, strict TS configuration, Next.js structure, PWA assets, Compose, env example, and app health endpoint.
- [ ] Add database schema and versioned migration for bootstrap, accounts, sessions, members, tasks, events, lists, meals, recipes, inventory, rewards, audit records.
- [ ] Record setup and deployment constraints.

### Task 2: Authentication and persistence services

- [ ] Implement safe first-run initialization, password hashing, session creation/rotation/revocation, and server-side membership checks.
- [ ] Implement validated CRUD and idempotent completion services for initial planner modules.
- [ ] Add auth and household-isolation tests.

### Task 3: Household UI and PWA

- [ ] Build login/setup and responsive Today, Calendar, Tasks, Meals, Lists, More, and settings experiences backed by APIs.
- [ ] Add light/dark/system styles, connection state, install metadata, service worker shell, and non-sensitive local view cache.
- [ ] Add accessible labels, responsive layouts, and empty/error states.

### Task 4: Operational readiness and truthful reconciliation

- [ ] Add backup/restore scripts, security/deployment docs, CI, and upgrade notes.
- [ ] Run install, lint, type check, unit/integration, and production build when dependencies and services are available.
- [ ] Update implementation status, limitations, and feature parity from executed evidence only.
