# Household API

All routes are same-origin JSON. Except setup/login/health, routes require the HTTP-only session cookie. Every mutation requires an Origin matching the request host and a CSRF token in the JSON body. Request bodies are limited to 32 KiB. Errors use a short `{ "error": "…" }` message; unexpected failures receive an opaque request ID.

| Method and path | Behavior |
|---|---|
| `GET /api/health` | Liveness check |
| `GET /api/setup-state` | Whether first-run setup is complete |
| `POST /api/setup` | One-time owner + household creation |
| `POST /api/login` | Local username/password session |
| `GET /api/me` | Current session and refreshed CSRF token |
| `POST /api/logout` | Revoke current session |
| `POST /api/password` | Change own password and revoke other sessions |
| `GET /api/members` / `POST /api/members` | List or add a member (owner/admin add) |
| `GET /api/items?kind=task` | List household records by kind |
| `POST /api/items` | Create event/task/shopping/meal/recipe/inventory/reward/announcement record |
| `POST /api/items/{id}/complete` | Complete an item with required `expectedVersion` and `mutationId`; household/actor-scoped receipt makes exact operation replay idempotent. Returns 401 for an expired session, 403 for denied role, 404 for missing item, 409 for a stale version, or 422 for an invalid operation. |
| `GET /api/summary` | Household counts and derived point balances |
| `GET /api/events` | Authenticated household-scoped Server-Sent Events; clients refetch state after a change or reconnect |

This is the existing alpha API, not OpenAPI-complete and not a stable integration contract. There is no pagination cursor or edit/delete endpoint yet. The completion handler's authenticated HTTP behavior has not been exercised in this environment because local socket creation is denied.


## Domain routes

Authenticated reads use `GET`. Writes use a session, CSRF token and a canonical UUID `mutationId`. Updates and decisions also accept the record's current `expectedVersion`. Domain mutations keep receipts and return a conflict for stale versions or reuse with a different request.

| Area | Routes |
|---|---|
| Today | `GET /api/dashboard` |
| Calendar | `GET/POST /api/calendar`, `PUT/DELETE /api/calendar/{id}`, `GET /api/calendar/export`, `POST /api/calendar/import` |
| Shopping | `GET /api/shopping`, `POST /api/shopping/lists`, `POST /api/shopping/lists/{id}/items`, `PUT/DELETE /api/shopping/items/{id}`, `POST /api/items/{id}/complete` |
| Chores | `GET/POST /api/chores`, `PUT/DELETE /api/chores/{id}`, `POST /api/chores/{id}/complete`, `POST /api/chores/occurrences/{id}/review` |
| Rewards | `GET/POST /api/rewards`, `PUT/DELETE /api/rewards/{id}`, `POST /api/rewards/{id}/request`, `POST /api/rewards/redemptions/{id}/review` |
| Recipes and meals | `GET/POST /api/recipes`, `GET/POST /api/meals`, `PUT/DELETE /api/recipes/{id}` and `/api/meals/{id}`, `POST /api/meals/groceries` |
| Inventory and announcements | `GET/POST /api/inventory`, `PUT/DELETE /api/inventory/{id}`, `POST /api/inventory/{id}/stock`, `GET/POST /api/announcements`, `PUT/DELETE /api/announcements/{id}`, `POST /api/announcements/{id}/ack` |
| Habits and allowance | `GET/POST /api/habits`, `PUT/DELETE /api/habits/{id}`, `POST /api/habits/{id}/check`, `GET/POST /api/allowance` |
| Six | `GET/POST /api/six`, `POST /api/six/{id}/decision` |

The original `/api/items` endpoints are retained for compatible alpha clients. The browser uses the domain-specific routes for new workflows.
