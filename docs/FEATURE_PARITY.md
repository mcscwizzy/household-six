# Feature parity and acceptance evidence

Status terms: **Complete and tested**, **Implemented but unverified**, **Partial**, **Blocked by environment**, **Blocked by external configuration**, **Incomplete**. A feature is complete only when persistence, server authorization, UI behavior and its relevant automated checks are present and executed.

| Requirement area | Status | Acceptance evidence / remaining work |
|---|---|---|
| Local household accounts and sessions | Partial | Local setup/login/password hashing/CSRF/cookies exist. Full role matrix, device/session manager, admin-assisted reset, disabling UI, parent PIN and complete session lifecycle tests remain. |
| Household isolation and role controls | Partial | Household-scoped queries and member-role creation guard exist. Only owner can add admins. Comprehensive operation-by-operation permissions and HTTP isolation tests remain. |
| Offline identity and mutation safety | Partial | Arbitrary cache discovery removed; no records cached; member-keyed IndexedDB completion queue; offline reload signed out; version + mutation ID; status-aware result handling. Real browser/API tests unavailable. No encryption or offline revocation guarantee. |
| Today dashboard | Partial | Existing summary and lists work. Household-local date boundaries, due-today/upcoming/overdue separation, truthful stats and real quick-add menu remain. |
| Calendar and integrations | Incomplete | Basic event records exist. Day/week/month/agenda, multiple calendars, recurrence/exceptions, timezone/DST, reminders, birthdays, ICS, CalDAV and optional Google/Outlook/iCloud integrations are not implemented. |
| Tasks, chores, routines and habits | Partial | Generic task/list records and idempotent point grant exist. Occurrences, recurrence templates, subtasks, approvals, routine steps, streaks, reminders and history remain. |
| Rewards, redemptions and allowance | Partial | Task points ledger exists. Reward store, approval workflow, redemption, allowance ledger and overdraft prevention remain. |
| Meal plan, recipes and groceries | Partial | Generic meal/recipe/list records exist. Weekly meal grid, structured ingredients, scaling, imports, deterministic aggregation, pantry-aware grocery generation and shopping mode remain. |
| Pantry, refrigerator and freezer | Partial | Generic inventory list only. Locations, quantities, units, thresholds, expiration, consumption/restocking, barcodes and reminders remain. |
| Household maintenance and vehicles | Incomplete | Assets, recurring service/mileage schedules, cost and completion history absent. |
| Announcements and devotional | Partial | Basic announcement records exist. Pin/expiry/targeting/acknowledgments absent. Devotional content, references, prayers and reading plans absent. |
| Documents and emergency information | Incomplete | No authenticated upload, access-controlled search/preview or emergency data model. |
| Budgeting | Incomplete | No manual income/bills/expenses/goals or exact-currency summaries. No banking integrations are planned. |
| Photos and command-center display | Incomplete | No album/media upload, slideshow, display session, hours or overlays. |
| PWA and household visual system | Partial | Existing responsive shell, manifest, service worker and SVG mark. Requested generated PNG/Apple/maskable icons, viewport test matrix, dark-mode QA, screenshots and physical iPhone test absent. |
| SSE and background scheduling | Partial | Household-scoped process-local SSE with reconnect behavior exists. Durable revision/replay, cross-worker coordination, persistent scheduler, leases/recovery and notifications absent. |
| Six assistant and local AI | Incomplete | No Ollama integration, deterministic intents, pending action review, OCR jobs or evaluation suite. Default remains disabled. |
| Private MCP | Incomplete | SDK/transport/tokens/scopes/audit tools absent and disabled. No external tunnel is configured. |
| NAS deployment and backups | Partial | Existing Dockerfile/Compose and SQLite online backup/restore exist. Compose plugin unavailable; current config does not yet run FastAPI; files/config backups and disposable container restart/restore drill remain. |
| CI, integration and browser testing | Blocked by environment | Existing unit tests pass. Local sockets, Compose, Playwright and registry access are unavailable. Add/execute supported CI coverage before production. |

The full continuation requirements, including optional providers, Apple connectivity constraints, security limits and deployment constraints, remain in the project mission and are not waived by this parity table. See [REQUIREMENTS.md](REQUIREMENTS.md) and [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).
