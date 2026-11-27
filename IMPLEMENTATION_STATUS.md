# Implementation status

Updated November 27, 2026. The feature matrix tracks the full product backlog.

| Area | Available workflows |
|---|---|
| Runtime | FastAPI on Uvicorn, SQLAlchemy with SQLite/WAL, transactional Alembic upgrades that preserve alpha data, and hashed runtime and browser dependency locks. |
| Calendar | Month, week, day and agenda, event CRUD, member colors, filters, start/end and all-day events, recurrence, skipped dates and iCalendar exchange. |
| Chores and rewards | Individual, parallel or shared assignments, morning and bedtime routines, once/daily/weekly scheduling, completion history, adult review, point ledger and reward redemption. |
| Meals and shopping | Structured ingredients, serving adjustments, weekly meal slots, repeatable grocery sync, categorized shared lists and authenticated offline completion. |
| Dashboard and extensions | Household-local Today, upcoming events, overdue chores, meals, shopping and points. Food inventory with stock history, pinned announcements and a read-only household display. |
| Six and MCP | Optional Ollama job queue with typed proposals and explicit approval. Optional local stdio MCP with expiring scoped credentials, audited reads and grocery proposals. |

The verification paths are in [testing](docs/TESTING.md) and [AI evaluation](docs/AI_EVALUATION.md). The [feature matrix](docs/FEATURE_PARITY.md) and [known limitations](docs/KNOWN_LIMITATIONS.md) cover remaining extensions and device checks.
