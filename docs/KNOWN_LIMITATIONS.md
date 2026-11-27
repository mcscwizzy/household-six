# Known limitations

This repository is still an early runnable alpha, not a complete Skylight alternative.

## Runtime and environment

- The approved target is Python + FastAPI/Uvicorn + SQLite/WAL + SQLAlchemy/Alembic. The checked-in runtime remains the dependency-free `ThreadingHTTPServer` / `sqlite3` service because PyPI package lookup failed in a temporary venv (`No matching distribution found for fastapi`) and npm registry DNS failed (`ENOTFOUND`). The target stack has not been silently replaced or claimed as implemented.
- Local socket creation is denied by the current environment, so HTTP integration tests cannot run. Docker Compose is missing and `docker info` was denied access to `/var/run/docker.sock`; container restart and image runtime behavior are unverified.
- Playwright is not installed; browser screenshots, Chromium/WebKit journeys and responsive viewport checks were not run.
- Git reports `origin/master` as default but cannot write feature refs under the read-only `.git` boundary. No branch, commit, push or PR was created.

## Security and data

- Offline reload is signed out. The browser no longer discovers another member's cache. Household records are not persisted in browser storage. IndexedDB contains only member-keyed task completion intents; the browser store is not encrypted and disconnected revocation cannot be guaranteed.
- Completion API changes and additive migration 002 are unit-tested at domain/migration level, but the full authenticated HTTP flow is unverified. The role-permission matrix, account disable/reset user flows, parent PIN, and persistent rate limits remain incomplete.
- The existing application is not independently security-reviewed and should remain behind trusted local HTTPS and restricted LAN ingress.
- No production data directory was available. The migration test preserved disposable alpha-shaped records; do not treat that as a migration of a household's actual database.

## Incomplete product and operations

- Domain tables, complete CRUD/search/filter/sort, dedicated module interfaces and the full permission matrix are incomplete.
- Calendar recurrence, exceptions, timezone/DST calculations, reminders, ICS and provider integrations are absent.
- Routines, habits, reward redemption, allowance, structured recipes, meal calendars and deterministic grocery generation are absent.
- Pantry history/barcodes, maintenance, vehicles, announcements workflow, devotional, secure documents, emergency information, budgeting, photo/video albums and wall display are absent.
- Durable SSE replay, background scheduler, notifications, Ollama assistant, AI evaluation, private MCP, uploads and coordinated file/database backup are absent.
- The manifest uses the existing SVG marks. Requested dedicated PNG, Apple Touch, maskable raster icons, dark-mode/mobile layout validation and iPhone verification have not been completed.
- Synology setup, trusted local HTTPS, physical iPhone/iPad behavior, resource limits and restore/rollback drill have not been verified.
