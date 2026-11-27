# Implementation status

Updated: 2026-11-27. This status is evidence-based; a screen or table does not count as feature completion.

## Working in this alpha

- [x] Local first-run household owner creation, scrypt password hashes, HTTP-only SameSite session cookie, sign-in/out, password change, failed-login throttling, and role checks for display and child task behavior.
- [x] Household member creation, household-scoped item queries/mutations, SQLite constraints, WAL, transactional task completion, points ledger unique constraint, audit entries.
- [x] Persisted basic events, tasks, shopping entries, meals, recipes, inventory, rewards, announcements.
- [x] Mobile-first Today, Calendar list, Tasks, Meals, More, members and settings; light/dark/system theme; original SVG mark; manifest and service worker shell.
- [x] Last-view cache and retry queue for task/list completion; ordinary writes require the server.
- [x] Household-scoped Server-Sent Events notify connected clients and trigger a fresh read on reconnect/change; backed by a bounded in-process queue.
- [x] Local backup archive and validated restore to an empty target.
- [x] Dependency-free domain/persistence tests for household query isolation, child/display rules, duplicate point prevention, multi-household SSE fanout, password hashing, multi-tab CSRF, and backup/restore.

## Important incomplete areas

- [ ] Requested Next.js/TypeScript, PostgreSQL, Drizzle, pnpm lockfile, and database migrations are not implemented. SQLite is used because npm registry access failed in this environment.
- [ ] Full role/permission matrix, invitations, PIN-protected profile switching, member/device management, admin reset, session revocation UI, RLS, and comprehensive request rate limiting are incomplete.
- [ ] Calendar views, categories/calendars, recurrence/RFC 5545 exceptions, timezone/DST handling, reminders, attachments, import/export, CalDAV and provider sync are incomplete.
- [ ] Task occurrences, routine builder, habits/streaks, approval workflow, reward catalog/redemption, allowance ledger, and chore history are incomplete.
- [ ] Recipes are basic text records; structured import, ingredient data/scaling, meal integration, grocery aggregation, scanning, and rich inventory transactions are incomplete.
- [ ] Maintenance, vehicles, devotional, secure document storage, emergency info, budgeting, photo/video albums, and full command-center mode are incomplete.
- [ ] SSE has no durable replay log and was not HTTP-tested; robust IndexedDB entity cache/version reconciliation, safe offline multi-user isolation and conflict resolution are incomplete.
- [ ] Notification scheduler, Web Push, Ollama assistant, AI import/confirmation/evaluations, and MCP are not implemented.
- [ ] OpenAPI, full CI, dependency scanning, vulnerability scan, Playwright journeys, browser screenshots, resource measurements, and physical iPhone/NAS verification have not been performed.
- [ ] PNG 192/512 and dedicated Apple touch/maskable icons are not included; only original SVG icons ship.

## Commands exercised

- `python3 -m unittest discover -s tests -v` — passed, 8 tests (domain, persistence, household event fanout, CSRF token reuse, backup/restore).
- `python3 -m compileall -q app tests scripts` — passed.
- `node --check app/static/app.js` — passed.
- PyYAML parsed `compose.yaml` and found both services; Docker Compose CLI validation remains unavailable.
- `python3 -m pytest -q` — passed, 8 tests.
- HTTP listener / integration tests — blocked: sandbox denies socket creation (`PermissionError: Operation not permitted`).
- `docker build --tag household-six:local .` — passed (legacy builder; image built).
- Container run / health check — blocked by Docker API permission denial on `docker run`.
- Compose CLI validation and Compose deployment — not available: Docker Compose plugin is missing.
- Dependency installation / production build — not available: npm registry DNS resolution failed; this implementation uses no third-party runtime packages.
- No browser screenshots, physical iPhone, NAS, load, or security scan were run.
- Final review was a manual self-review; an independent review was unavailable under the no-subagent instruction. The workspace `.git` directory is empty and read-only, so no Git history or commits could be created.
