# Testing

## Locally available checks

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q app tests scripts
node --check app/static/app.js
```

The most recent executed unit run passed 16 tests: password hashing, multi-tab CSRF, household-scoped item queries, child/display restrictions, exactly-once point awards, household SSE fanout, preservation during migration from an unversioned v1 schema, owner-only administrator creation, child/display item-create restrictions, stale entity version conflict, mutation receipt uniqueness, canonical UUID validation, expired/disabled session rejection, rejection of calendar event completion, and backup/restore. Python compilation and JavaScript syntax checks also passed.

Baseline before changes: 8 tests passed. Current total: 16 tests passed.

## Environment blockers

- Creating a local socket fails with `PermissionError: [Errno 1] Operation not permitted`; authenticated HTTP integration cannot run in this workspace.
- Docker is installed, but `docker compose` reports that the Compose plugin is unavailable. Compose build, health, restart and persisted-data tests have not run.
- Playwright is not installed and npm registry DNS fails. Chromium and WebKit end-to-end tests and screenshots have not run.
- PyPI package resolution from a new temporary Python virtual environment returns `No matching distribution found for fastapi`; FastAPI/Uvicorn/SQLAlchemy/Alembic/MCP installation and app migration tests against those packages have not run.

The repository now defines CI jobs for actual Compose authenticated HTTP operations and persisted state across restart, plus Playwright Chromium/WebKit login/task/offline flows, responsive widths and light/dark screenshot artifacts. They are authored but have not run; do not report them as passing.

Do not mark any blocked check as passed. CI should run the Python checks, start Compose, wait for `/api/health`, create a disposable household, exercise authenticated item operations, restart the app and confirm persistence. Add Playwright Chromium and WebKit, dependency audit and security scanning in a registry-enabled runner before deployment.
