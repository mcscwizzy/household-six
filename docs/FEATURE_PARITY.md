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
| Tasks, chores, routines and habits | Partial | Generic task/list records and idempotent point grant exist. Occurrences, recurrence templates, subtasks, approvals, routine steps, streaks, reminders and history remain. |
| Rewards, redemptions and allowance | Partial | Task points ledger exists. Reward store, approval workflow, redemption, allowance ledger and overdraft prevention remain. |
| Meal plan, recipes and groceries | Partial | Generic meal/recipe/list records exist. Weekly meal grid, structured ingredients, scaling, imports, deterministic aggregation, pantry-aware grocery generation and shopping mode remain. |
| Pantry, refrigerator and freezer | Partial | Generic inventory list only. Locations, quantities, units, thresholds, expiration, consumption/restocking, barcodes and reminders remain. |
| Household maintenance and vehicles | Incomplete | Assets, recurring service/mileage schedules, cost and completion history absent. |
| Announcements and devotional | Partial | Basic announcement records exist. Pin/expiry/targeting/acknowledgments absent. Devotional content, references, prayers and reading plans absent. |
| Documents and emergency information | Incomplete | No authenticated upload, access-controlled search/preview or emergency data model. |
| Budgeting | Incomplete | No manual income/bills/expenses/goals or exact-currency summaries. No banking integrations are planned. |
| Photos and command-center display | Incomplete | No album/media upload, slideshow, display session, hours or overlays. |
| PWA and household visual system | Partial | Existing responsive shell, manifest, service worker and SVG mark. PNG, Apple touch and maskable icons are included. Chromium and WebKit exercised 320–1440 px viewports with light and dark screenshots. Physical iPhone testing remains. |
| SSE and background scheduling | Partial | Household-scoped process-local SSE with reconnect behavior exists. Durable revision/replay, cross-worker coordination, persistent scheduler, leases/recovery and notifications absent. |
| Six assistant and local AI | Incomplete | No Ollama integration, deterministic intents, pending action review, OCR jobs or evaluation suite. Default remains disabled. |
| Private MCP | Incomplete | SDK/transport/tokens/scopes/audit tools absent and disabled. No external tunnel is configured. |
| NAS deployment and backups | Partial | Existing Dockerfile/Compose and SQLite online backup/restore exist. A disposable loopback Compose project ran Uvicorn, preserved an authenticated completion through restart and restored to a separate local volume. Files/config backup and physical NAS verification remain. |
| CI, integration and browser testing | Partial | The Python unit and live HTTP suite, local Compose build/restart/restore, and Playwright Chromium and WebKit passed locally. Check GitHub Actions separately. |

The full continuation requirements, including optional providers, Apple connectivity constraints, security limits and deployment constraints, remain in the project mission and are not waived by this parity table. See [REQUIREMENTS.md](REQUIREMENTS.md) and [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).
