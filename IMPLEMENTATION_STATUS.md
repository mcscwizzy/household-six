# Implementation status

Updated: 2026-11-27. Status is evidence-based. A screen, route or table alone does not mean a feature is complete.

## Complete and tested

- Python 3.12 / SQLite alpha unit and persistence checks; see exact run below.
- Household-scoped item list and completion domain helpers, salted scrypt password hashing, multi-tab CSRF tokens, and point-award uniqueness in the existing alpha.
- Additive schema migration ledger and migration 002 for disabled-account state and unique mutation receipts. Tests verify alpha IDs and records survive upgrade from an unversioned v1 schema.
- Server-side member-role creation policy: only the owner can create administrators; owners and admins can add lower-privilege member profiles.
- Server-side record creation policy: children may add task and shopping records only; display sessions cannot create records. The child form hides adult assignment and point controls.
- Session lookup rejects expired sessions and sessions belonging to disabled accounts; session revocation is still limited to existing logout/password-change flows.
- Completion domain helper rejects calendar events and other non-completable record kinds; only tasks and shopping entries support generic completion.
- Mutation identifiers are required to be canonical UUIDs; receipt table uniqueness is household-scoped and avoids storing private result bodies.

## Implemented but unverified

- Client and API versioned completion flow in a real browser/HTTP session. Local socket creation is denied, so no end-to-end HTTP behavior was exercised.
- Completion handler validates expected version and mutation ID, returns typed conflict/validation/not-found/authorization statuses, and uses unique household-scoped receipts. Handler status behavior and exact replay response remain unverified over HTTP.
- Offline identity remediation in the browser: arbitrary localStorage cache selection removed; no household record cache is persisted; IndexedDB stores only member-keyed completion intents; unauthenticated offline reload is signed out; logout and detected session revocation clear that member's intents. Browser behavior remains unverified.
- Client completion distinguishes 401/403/404/409/422 and bounded transient retries. Offline intents are processed only after the same member reauthenticates. Browser/API behavior remains unverified.
- Exact mutation receipt replay behavior through the handler. Unit coverage verifies database uniqueness, not authenticated HTTP replay.
- Migration path against an alpha database. Tests create an unversioned v1 schema and verify preserved IDs, password hashes, timestamps, assignments and ledger entries; no production household database was present to migrate.

## Partial

- Existing local auth, sessions, household members, list-item create/read, task completion, SSE fanout, PWA shell and backup scripts.
- Security policy, role matrix, date handling, module CRUD, and current static JavaScript organization.
- Docker image definition and Compose deployment files from the alpha.

## Blocked by environment

- FastAPI, Uvicorn, SQLAlchemy, Alembic and Python MCP SDK installation: none are installed; package resolution in a temporary venv reported no matching package versions. npm registry DNS returned `ENOTFOUND`. Direct target dependency versions are pinned in requirements files; a transitive lock could not be generated here.
- HTTP integration tests and browser E2E: local socket creation raises `PermissionError`; Playwright is not installed.
- Compose build/start, restart-persistence test and container health: Docker is present but Compose CLI is absent; `docker info` was denied access to `/var/run/docker.sock`.
- Git feature branch, commits and PR: Git identifies `origin/master` as the default, but cannot write `.git/refs` under the provided read-only metadata boundary. Current source changes remain uncommitted on the baseline worktree.

## Incomplete

- FastAPI/Uvicorn runtime, SQLAlchemy models/session handling, Alembic environment, modular service package layout, and a complete reproducible dependency lock.
- Dedicated normalized domain tables and data backfill for calendar, chores/routines/habits/rewards, meals/recipes/groceries, inventory, maintenance, vehicles, announcements, devotional, documents, emergency data, budgeting, photos and display mode.
- Complete role-permission matrix, password reset UI, member disabling UI, parent PIN, account/session management, trusted-proxy configuration, rate limiting, request timeouts, and full CSRF/security review.
- Calendar views, recurrence/exceptions, local timezone/DST behavior, reminders, ICS, CalDAV and provider integrations.
- Persistent job scheduler, durable SSE replay, cross-worker distribution, local assistant, AI evaluations, and private MCP.
- Purpose-built complete CRUD user interfaces for all modules, accurate Today date filtering, dark-mode/accessibility/viewport QA, requested PNG/icon set, and browser screenshots.
- Full Compose production hardening, Synology verification, upload backup/restore, and rollback drill.
- CI execution, Compose/browser test results, live AI evaluation and resource measurements. CI definitions for CodeQL, Compose restart persistence and Playwright browser flows exist but have not run.

## Verification run

- Starting commit: `18fa622ac79d8edecf9e7e30333e3fbbe3d8d1f5` on `master`.
- Baseline: `python3 -m unittest discover -s tests -v` — 8 tests passed.
- Current implementation: `python3 -m unittest discover -s tests -v` — 16 tests passed.
- `python3 -m compileall -q app tests scripts` — passed.
- `node --check app/static/app.js` — passed.
- No Compose, HTTP, browser, iPhone, NAS, AI inference, MCP, load, or security-scan result is claimed.
- CI defines unit/static checks, CodeQL analysis, authenticated Compose persistence across restart, and Playwright Chromium/WebKit viewport/offline checks with screenshot artifacts. These jobs have not run yet.
