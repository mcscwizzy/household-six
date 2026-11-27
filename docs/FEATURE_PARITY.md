# Feature parity and acceptance evidence

Status terms: **Complete and tested**, **Implemented but unverified**, **Partial**, **Blocked by environment**, **Blocked by external configuration**, **Incomplete**. A feature is complete only when persistence, server authorization, UI behavior and its relevant automated checks are present and executed.

| Requirement area | Status | Acceptance evidence / remaining work |
|---|---|---|
| Local household accounts and sessions | Partial | Local setup/login/password hashing/CSRF/cookies exist. Full role matrix, device/session manager, admin-assisted reset, disabling UI, parent PIN and complete session lifecycle tests remain. |
| Household isolation and role controls | Partial | Household-scoped queries and member-role creation guard exist. Only owner can add admins. Comprehensive operation-by-operation permissions and HTTP isolation tests remain. |
| Offline identity and mutation safety | Partial | Arbitrary cache discovery removed; no records cached; member-keyed IndexedDB completion queue; offline reload signed out; version + mutation ID; status-aware result handling. Chromium and WebKit exercise shopping completion, reconnect and signed-out offline reload. No encryption or offline revocation guarantee. |
| Today dashboard | Partial | The authenticated dashboard uses the household timezone for appointments, upcoming events, dated chores and meals. It includes open shopping counts and ledger balances. |
| Calendar and integrations | Partial | Month, week, day, agenda, member colors and filters, event CRUD, timed and all-day events, daily-to-yearly recurrence, skipped dates and iCalendar exchange run locally. Updated-instance imports, multiple calendars, reminders, birthdays, CalDAV and optional Google/Outlook/iCloud integrations remain. |
| Shopping | Complete and tested | Multiple lists, categorized items, quantities, editing, deletion, shopping mode, household SSE and offline completion. Live HTTP, Chromium and WebKit exercised. |
| Tasks, chores, routines and habits | Partial | Daily and weekly chores, shared and individual assignments, morning and bedtime grouping, history, and adult approval are implemented. Habits, streaks, subtasks and reminders remain. |
| Rewards, redemptions and allowance | Partial | Reward store, adult approval, redemption and transactional balance checks are implemented. Allowance remains. |
| Meal plan, recipes and groceries | Partial | Weekly meal slots, structured recipes, scaling and deterministic grocery sync are implemented. Pantry-aware subtraction and additional recipe import formats remain. |
| Pantry, refrigerator and freezer | Partial | Pantry, refrigerator and freezer locations, exact quantities, units, expiry, low stock, consumption/restocking and recent history are implemented. Barcodes and reminders remain. |
| Household maintenance and vehicles | Incomplete | Assets, recurring service/mileage schedules, cost and completion history absent. |
| Announcements and devotional | Partial | Household-wide announcements support pinning, expiry and per-member acknowledgment. Targeting, devotional content, prayers and reading plans remain. |
| Documents and emergency information | Incomplete | No authenticated upload, access-controlled search/preview or emergency data model. |
| Budgeting | Incomplete | No manual income/bills/expenses/goals or exact-currency summaries. No banking integrations are planned. |
| Photos and command-center display | Partial | The household display shows the local clock, appointments, chores, meals and pinned announcements. Photo albums, slideshows and display scheduling remain. |
| PWA and household visual system | Partial | Existing responsive shell, manifest, service worker and SVG mark. PNG, Apple touch and maskable icons are included. Chromium and WebKit exercised 320–1440 px viewports with light and dark screenshots. Physical iPhone testing remains. |
| SSE and background scheduling | Partial | Household-scoped process-local SSE with reconnect behavior exists. Six has a bounded persistent queue with interrupted-job recovery. Durable SSE replay, cross-worker coordination, general reminders and notifications remain. |
| Six assistant and local AI | Partial | Local Ollama, typed proposals with adult confirmation, scoped queries, recipe extraction and document/image text extraction. Six evaluated six synthetic text cases locally. Broader evaluation remains. |
| Private MCP | Complete and tested | Optional stdio transport, expiring scoped credentials, live revocation, audited reads and optional grocery proposals. Tested with the installed Python SDK. |
| NAS deployment and backups | Partial | Existing Dockerfile/Compose and SQLite online backup/restore exist. A disposable loopback Compose project ran Uvicorn, preserved an authenticated completion through restart and restored to a separate local volume. Files/config backup and physical NAS verification remain. |
| CI, integration and browser testing | Partial | The Python unit and live HTTP suite, local Compose build/restart/restore, and Playwright Chromium and WebKit passed locally. Check GitHub Actions separately. |

The full continuation requirements, including optional providers, Apple connectivity constraints, security limits and deployment constraints, remain in the project mission and are not waived by this parity table. See [REQUIREMENTS.md](REQUIREMENTS.md) and [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).
