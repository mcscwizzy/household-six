# Product and acceptance requirements

This file records the active continuation requirements. The previous Next.js/PostgreSQL direction is superseded by [ADR 0001](adr/0001-approved-runtime-and-data-store.md), but none of the product scope below is waived. Refer to [FEATURE_PARITY.md](FEATURE_PARITY.md) and [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md) for evidence.

## Product and architecture

- Build a private, independently developed Skylight-style household planner for Synology/local hardware. Household data stays local. Core use must work without AI, hosted services, subscriptions, external identity, analytics or routine internet access.
- Use maintained Python 3.12+, FastAPI/Uvicorn, SQLite/WAL, SQLAlchemy, Alembic, modular JavaScript, IndexedDB, SSE and Docker Compose. Keep SQLite off SMB/NFS. Do not introduce PostgreSQL, Redis, Kubernetes, hosted infrastructure or a second architecture.
- Use shared application services for HTTP, UI, AI, MCP and background jobs. Keep provider integrations, Ollama, MCP and Caddy optional and disabled by default.
- Preserve alpha household/user/item IDs, password hashes, timestamps, assignments and point ledger entries during transactional versioned migrations.
- Keep the forest green, sage, warm cream and muted gold visual identity. Provide purpose-built family interfaces, not a CRUD administration shell.

## Security, identity and data integrity

- Treat browser input and state as untrusted. Scope every read and write server-side to the authenticated household; validate bodies; return generic failures; never log identifiers or private content.
- Support Owner, Administrator, Adult, Child and read-only display roles. Enforce a complete per-operation matrix server-side; prevent member role escalation; keep children from adult-only budget, emergency and document data.
- Implement expiring/revocable sessions, account disabling, administrator-assisted password reset and secure parent PIN checks for privileged shared-device actions.
- Offline policy must distinguish authenticated, offline-authorized and signed-out. Never select an arbitrary cached identity. Keep sensitive records out of offline storage; clear/isolate caches on logout, account changes and detectable revocation. Do not claim browser storage encryption or offline revocation guarantees.
- Queue only eligible writes after network failure. Use unique mutation IDs and expected entity versions. Handle 401 as reauthentication, 403 as rejection and rollback, 404 as missing-entity reconciliation, 409 as conflict resolution, 422 as validation feedback, and transient server failures with bounded backoff. Prevent stale, unauthorized and duplicate replay.
- Use secure cookies and CSRF protection; bounded request size/time, trusted-proxy configuration, rate limits, security headers, safe errors and graceful shutdown.
- Use SQLite foreign keys, indexes, WAL, short write transactions and referential integrity. Never replace/discard alpha household data during schema normalization.

## Core family planner

- **Today:** household-local date boundaries; distinguish today's, upcoming and overdue records; accurate persisted counts; useful empty/loading/error states; a true quick-add selector.
- **Calendar:** day/week/month/agenda; member colors and filters; multiple calendars; event create/edit; times, all-day/multi-day, category, location, recurrence and exceptions; edit one/future/all occurrences; timezone/DST correctness; birthdays/anniversaries; reminders; ICS import/export; optional ICS subscriptions, CalDAV, Google, Outlook and iCloud. External providers remain disabled until explicitly configured. Core calendar works offline from internet.
- **Tasks, routines, habits and rewards:** recurrence templates/occurrences; daily/weekly chores; shared/individual assignment, priority, due dates, subtasks, reminders, approvals and history; morning/bedtime/custom routines; household-local habit streaks; child-friendly completion; exactly-once atomic points; parent-approved reward redemption; no overdraft or duplicate redemption; immutable points/redemption/allowance transactions.
- **Meals, recipes and groceries:** weekly breakfast/lunch/dinner/snack planner; multiple recipes or free text per meal; history and leftovers; favorites; structured ingredients/units/instructions/timing/servings; scaling and metric/US units; categories/tags/search/cooking mode/pasted-text import; multiple shopping lists, categories, quantities, notes and shared completion; deterministic grocery aggregation and pantry-aware generation. Never invent measurements or conversions.

## Additional household modules

- **Pantry/fridge/freezer:** locations, quantities/units, expiry, low-stock thresholds, consumption/restocking history, barcode entry and reminders.
- **Maintenance:** assets, recurring schedules, assignments, completion history, seasonal templates and calendar integration.
- **Vehicles:** profiles, odometer, date/mileage maintenance, service/repair history and costs.
- **Announcements:** pinned/expiring messages, member targets, acknowledgments and calendar integration.
- **Devotional:** user-supplied content, scripture references, prayer requests/answered prayers, reading plans and progress; do not bundle copyrighted translations without permission.
- **Documents:** authenticated uploads outside public static paths, category/metadata, preview/download, access restrictions and search.
- **Emergency information:** contacts, procedures, utility shutoffs and optional medical notes with restricted access.
- **Budget:** manual income, recurring bills, expenses, categories, savings goals and monthly summary using exact currency arithmetic; no banking connections.
- **Photos/display:** albums, photo and optional video uploads, thumbnails/slideshow, clock/calendar overlays, display hours/quiet hours and restricted read-only sessions; avoid resource-heavy video processing.
- Every module needs real persistence, scoped APIs, a purpose-built UI and tests before it can be marked complete.

## PWA, live updates and jobs

- Provide original 192x192, 512x512, Apple Touch, maskable and favicon assets; valid standalone manifest; safe-area support; responsive bottom/desktop/tablet navigation; accessible touch targets; dark mode; reduced motion; offline shell; versioned assets; update handling; identity-bound IndexedDB and queue synchronization.
- Test widths 320, 375, 390, 430, 768, 1024 and 1440 pixels without horizontal overflow. Capture major interfaces in light and dark mode. Preserve in-progress forms during SSE refresh. Do not claim physical iPhone verification without a device.
- SSE requires authenticated household-scoped subscriptions, heartbeat/reconnect, durable revision/replay or missed-event reconciliation, session revalidation, bounded connections and clean shutdown. Do not use a process-local event hub across workers without coordination; begin with one process.
- Use a lightweight persistent SQLite scheduler with recurrence, leases, bounded retry and restart recovery for calendar/chore/habit/inventory/maintenance reminders, optional sync and local AI work. Persist in-app notifications. Web Push stays optional; document Apple's internet requirements.

## Optional local assistant and private MCP

- Six uses Ollama as a constrained interpreter, never an autonomous agent. Defaults: `AI_ENABLED=false`, provider `ollama`, `http://ollama:11434`, `qwen3.5:0.8b`, context 4096, temperature 0.1, one concurrent job, writes require confirmation, cloud fallback disabled.
- Support an existing LAN Ollama server without forcing a second instance. Optional bundled Ollama is limited to 2 CPU equivalents, 4 GB, one request/model, context 4096, keep-alive 0 and cloud features disabled. Verify model/API support; never auto-download larger models.
- Deterministic routing and bounded schemas cover calendar queries/proposals, chores, groceries, meal plans, recipe extraction, inventory, maintenance and household summaries. Application code resolves dates/members/quantities/permissions. Expose minimum context; no arbitrary SQL, shell, secrets, file/network access or executable imported text.
- All AI writes become validated pending actions bound to operation, identity and household; the user reviews/edits/confirms/rejects; ordinary authorization applies and confirmed writes are audited. OCR/document/image work is local, bounded and asynchronous.
- Maintain 100+ representative mocked requests covering ambiguity, invalid commands and prompt injection. Measure intent/field/schema accuracy, latency and resources separately from live inference. Target 95% simple-command accuracy; simplify deterministic parsing before considering a larger model. Never claim live model success without an executed evaluation.
- MCP uses the Python SDK, disabled by default; local stdio and authenticated Streamable HTTP where practical; scoped expiring/revocable tokens; household isolation; read-only default; explicit write permission; rate/origin validation and audit. Tools use application services and pending approval, never arbitrary SQL/shell/files. Do not tunnel automatically or imply cloud ChatGPT reaches a LAN-only endpoint.

## NAS, backup and verification

- Core Compose works without AI/MCP. Optional Caddy/Ollama/MCP profiles; configurable ports and bind mounts; existing Synology reverse proxy/Ollama supported; LAN-only default; no published DB/AI endpoints; non-root, health/readiness, versioned migrations, resource/log limits, secrets, graceful shutdown and persistent storage.
- Document trusted HTTPS/DNS for `householdsix.home.arpa`, configurable ingress, no automatic firewall edits and no internet requirement for ordinary core use after installation.
- Back up SQLite plus uploaded files/configuration; test restore only into disposable data. Never overwrite production during tests. Document backup and rollback.
- Automated checks must cover auth/session/CSRF/roles/household isolation; CRUD modules; alpha migration; concurrency; recurrence/DST; points/rewards; groceries/recipe scaling; budgets; offline identity/conflicts; SSE; scheduler recovery; upload authorization; AI action validation; MCP authorization; backup/restore.
- Playwright Chromium and WebKit; actual Compose health/authenticated HTTP/restart-persistence integration in CI; dependency audit/security scan where supported. Report exactly which commands and workflows ran. Do not call CI green before it runs.
- Final verification must distinguish tested behavior from unverified, environment-blocked and externally configured items. No invented parity percentages, AI benchmarks, NAS/iPhone checks, screenshots or resource measurements.
