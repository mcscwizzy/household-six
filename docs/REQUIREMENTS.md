# Requirements tracking

This repository is a partial, runnable alpha. Items marked incomplete are not implied to exist just because related data or navigation is present.

| Requirement area | Status | Evidence / note |
|---|---|---|
| Local setup and accounts | Partial | Owner initialization, username/password login, member add, role field, password change. Invitations, reset, session/device management and full authorization matrix remain. |
| Household isolation | Partial | Queries and mutations scope household ID; covered in HTTP test. No PostgreSQL RLS (SQLite backend). |
| Dashboard | Partial | Date/greeting, member points, task/event/meal/shopping counts and lists from persisted data. Reordering, notifications, birthdays, maintenance, weather and filters remain. |
| Calendar | Incomplete | Event records and list view only; recurrence, DST, integrations and export/import remain. |
| Tasks / chores | Partial | Persisted task record and atomic idempotent completion; routines, occurrence rules, approvals, evidence and history remain. |
| Habits and rewards | Incomplete | Generic reward entries and completion points only; habits, streaks, ledger-driven reward redemption remain. |
| Meals and recipes | Partial | Persisted manual meal and text recipe entries; structured ingredients, imports, scaling and meal-plan model remain. |
| Shopping / inventory | Partial | Shared persisted entries and completion; multiple lists, quantities, locations, expiration transactions and scanning remain. |
| Maintenance, vehicles, devotional, documents, budget, media | Incomplete | Not implemented. |
| PWA and offline | Partial | Manifest, SVG mark, shell cache, last-loaded list cache, queued completion. No IndexedDB, conflict reconciliation or native iPhone verification. |
| Real-time | Partial | Household-scoped in-process SSE notifications refresh clients; no durable replay log and HTTP behavior is unverified. |
| Notifications / integrations | Incomplete | Not implemented. |
| Local AI / MCP | Incomplete | Not implemented; planner works without AI. |
| Deployment / backup | Partial | App Compose service, optional Caddy profile, SQLite backup and safe restore script. No NAS execution or PostgreSQL service. |
| Security | Partial | Password hashing, HTTP-only cookie, origin check, CSRF token on writes, generic error, household scope, display role blocked, upload surface not present. Needs independent review and expanded rate limiting. |
| Testing | Partial | A few standard-library HTTP integration tests. No browser, load, fuzz, or device tests. |
