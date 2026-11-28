# Operation Homefront Continuation Plan

> **For agentic workers:** Execute this continuation inline, in order, using test-first changes and small commits. The user explicitly requested implementation to continue without a planning handoff.

**Goal:** Extend the verified Operation Breakthrough baseline toward a truthful Household Six release candidate while preserving local household data and all working flows.

**Architecture:** Continue the existing FastAPI/Uvicorn modular application, additive Alembic/SQLite migrations, local files, modular JavaScript, IndexedDB, SSE, and optional local Ollama/MCP. New modules must use household-scoped services and the existing authorization, mutation, and versioning patterns.

**Tech Stack:** Python 3.12, FastAPI/Uvicorn, SQLite/WAL, SQLAlchemy/Alembic, vanilla JavaScript, IndexedDB, Playwright, Docker Compose.

**Spec:** `docs/REQUIREMENTS.md` and the Operation Homefront mission in the user request.

## Global Constraints

- Keep household data local; do not add analytics, external identity, hosted databases, Redis, or a parallel architecture.
- Scope every protected read and write server-side by authenticated household; validate requests and use generic errors.
- Preserve existing IDs, password hashes, timestamps, assignments, mutation receipts, reward/allowance ledger entries, and migrations through additive migrations.
- Keep offline record storage opt-in and identity-bound; never cache financial, medical, emergency, or private document data.
- Keep Six local-only, constrained, confirmation-gated, and defaulted to `qwen3.5:0.8b`; keep MCP and external delivery disabled by default.
- Do not claim full parity, zero vulnerabilities, physical NAS/iPhone acceptance, live-model accuracy, or Compose success without executed evidence.
- Do not merge PR #1 or deploy to physical NAS without authorization.

## Review Focus

- Cross-household IDs must not disclose or mutate another household's records; test HTTP and service boundaries.
- Disabled accounts, revoked sessions, and role changes must take effect on the next request; test session revalidation.
- Recurring local dates must remain correct across timezone and daylight-saving transitions; test recurrence exceptions.
- Money and ledger entries must remain exact and non-duplicating; test rounding, retries, and stale versions.
- Files and offline records must not escape their identity, household, role, or cache boundary; test direct-object access and account switching.

## Workstreams

### Task 1: Preflight and verified baseline

- Confirm PR #1 state, current commit, clean working tree, continuation branch, active requirements, and known limitations.
- Run the Python, compileall, Playwright, and isolated Compose baselines where the environment permits; record exact failures and skips.

### Task 2: Account administration and authorization

- Add an explicit owner/administrator/adult/child/display permission matrix and enforce it at each protected operation.
- Complete profile edits, color/avatar validation, account disable/reactivation, assisted password reset, session/device listing and revocation, local invitation flow, managed child profiles, parent PIN, and shared-device switching.
- Add additive migrations, audit events without private values, bounded rate limits, and tests for escalation, revocation, disabling, and cross-household access.

### Task 3: Home and vehicle maintenance

- Add household-scoped assets, categories, assignments, date/mileage schedules, recurrence, seasonal templates, completion history, costs, notes, reminders, and calendar/Today integration.
- Add vehicle profiles and service, odometer, repair, registration, tire, and battery records without external vehicle services.
- Add tests and useful templates that remain inactive until accepted.

### Task 4: Devotional, emergency, and document records

- Add optional private/family devotionals, user-provided scripture content, reading plans, progress, prayer tracking, and reminders.
- Add adult-restricted emergency contacts, utility procedures, and user-provided medical/allergy information.
- Add authenticated local PDF/image storage outside static paths with bounded type/content/size validation, household and per-document authorization, safe download headers, and backup/restore coverage.

### Task 5: Manual household budgeting

- Add adult-only income, recurring bills, expenses, categories, monthly targets, obligations, savings goals, exact minor-unit arithmetic, historical summaries, and CSV export.
- Keep the allowance ledger separate and test household isolation, exact totals, and duplicate protection.

### Task 6: Persistent reminders and notifications

- Add bounded SQLite jobs with leases, deduplication, safe retry, restart recovery, persistent per-member notifications/read states, quiet hours, and preferences.
- Integrate calendar, chore, habit, meal, inventory, maintenance, vehicle, reward, and announcement reminders; keep external delivery opt-in.

### Task 7: Planner, offline, calendar, Six, and MCP completion

- Close chore checklist, routine-order, habit-frequency, achievement, allowance schedule, recipe, cooking, pantry-aware grocery, barcode, announcement-target, and dashboard gaps.
- Add calendar collections/categories, recurrence-instance editing/import, reminders, and timezone/DST regression coverage; external providers remain disabled and clearly separated as read-only or bidirectional.
- Add explicit opt-in offline access for only approved records, identity binding, expiry/lock/queue reconciliation, durable revisions or replay, and form-preserving refresh.
- Expand Six's deterministic routes, editable version-bound proposals, audit enforcement, 100+ fixture evaluation, and real local inference measurements only where local model access is available.
- Extend private MCP with scoped read tools and confirmation-gated proposals; keep credentials, transport, and audit controls local and disabled by default.

### Task 8: Photos and display mode

- Add local photo albums, captions, favorites, thumbnails, optional supported video, playback settings, schedule/quiet hours, screensaver, clock/calendar overlays, and configurable widgets.
- Enforce read-only display projections and sensitive-data exclusions; document iOS wake/fullscreen limits.

### Task 9: Household UI refinement

- Preserve the existing forest/sage/cream/gold identity while adding coherent navigation, accessible controls, light/dark states, useful empty states, and module-specific forms.
- Exercise populated synthetic data at 320, 375, 390, 430, 768, 1024, and 1440 px; capture only screenshots produced by actual browser runs.

### Task 10: NAS readiness, documentation, and release evidence

- Reconcile Compose resource/security/health/backup/reverse-proxy configuration and Synology/Caddy guidance with actual behavior.
- Update README, AGENTS, CHANGELOG, implementation status, feature parity, limitations, security, AI, MCP, backup, and Synology docs from executed evidence.
- Run requested regression, migration, authorization, restore, browser, audit, and integration checks where available; prepare a proposed v1.0 release candidate without calling it final production.
- Report commit, PR, feature matrix, test counts, CI, screenshots, live AI results, resource evidence, deployment/rollback instructions, acceptance checklist, and remaining blockers without inventing unavailable evidence.
