# Implementation status

Updated November 27, 2026. The feature matrix tracks the full product backlog.

| Area | Available workflows |
|---|---|
| Runtime | FastAPI on Uvicorn, SQLAlchemy with SQLite/WAL, transactional Alembic upgrades through version 14 that preserve alpha data, and hashed runtime and browser dependency locks. |
| Accounts and roles | Explicit five-role permission matrix; profile name/color/avatar edits; account disable/reactivation; administrator-assisted password reset; self-device management; owner/administrator member session listing and revocation. Local invitation, parent PIN, managed profile and shared-device switching flows remain. |
| Calendar | Month, week, day and agenda, event CRUD, member colors, filters, start/end and all-day events, recurrence, skipped dates and iCalendar exchange. |
| Chores and rewards | Individual, parallel or shared assignments, morning and bedtime routines, once/daily/weekly scheduling, completion history, adult review, point ledger and reward redemption. |
| Meals and shopping | Structured ingredients, serving adjustments, weekly meal slots, repeatable grocery sync, categorized shared lists and authenticated offline completion. |
| Dashboard and extensions | Household-local Today, upcoming events, overdue chores, meals, shopping and points. Adult Today views also show upcoming home maintenance and vehicle/registration reminders. Food inventory with stock history, pinned announcements, a read-only household display, daily habit streaks and an allowance ledger. |
| Property care | Adult-managed home assets, categories, assignments, one-time and recurring date schedules, seasons, instructions, notes, costs and completion history. Seven templates are suggestions and do not create schedules until saved. Vehicle profiles support gasoline, diesel, hybrid and electric vehicles, VIN, odometer, date/mileage intervals, service records, registration reminders and costs. Supporting files and a general notification scheduler remain unavailable. |
| Six and MCP | Optional Ollama job queue with typed proposals and explicit approval. Optional local stdio MCP with expiring scoped credentials, audited reads and grocery proposals. |

Verification on this branch: 43 unit tests discovered (28 passed, 15 environment-gated skips), 14 live HTTP tests (12 passed, 2 Ollama-gated skips), and 26 Chromium/WebKit screenshots across the core planner and new property-care screens. The Docker Compose v1.29.2 container built and reached healthy status; an authenticated task/session survived restart, and a separate restore volume passed SQLite integrity plus owner/task checks. See [testing](docs/TESTING.md), [AI evaluation](docs/AI_EVALUATION.md), the [feature matrix](docs/FEATURE_PARITY.md) and [known limitations](docs/KNOWN_LIMITATIONS.md). GitHub CI for this branch has not run because it has not been pushed.
