# Household Six Design

## Intent

Build a private, self-hosted household organizer for an iPhone-first family. The local server remains authoritative, data stays in PostgreSQL and local file storage, and core workflows do not depend on AI or cloud services.

## Goals

- Deliver a deployable modular monolith with secure local accounts and household-scoped data.
- Ship a useful responsive PWA with working Today, Calendar, Tasks, Meals, Lists, Rewards, Inventory, and household settings flows.
- Include optional local AI/MCP boundaries, Compose deployment, backups, and accurate feature status.

## Non-goals

- No cloud identity, telemetry, banking connection, external AI fallback, public registration, or public deployment.
- No claim of full Skylight parity or physical iPhone/NAS validation without access to that hardware.

## Constraints

- Use TypeScript, Next.js App Router, PostgreSQL, Drizzle, Zod, and Docker Compose where practical.
- The app must remain usable with AI disabled, support trusted local HTTPS, and preserve data across restarts.
- Protect household boundaries on the server; use idempotency for repeatable completion actions.

## Approaches

1. **Broad prototype with mock services:** fast screens, but violates persistence and security requirements. Rejected.
2. **Modular monolith with an operational core and explicitly staged modules:** shared authenticated services, real relational persistence, and product surfaces that can expand without microservices. Selected because it fits the NAS and single-maintainer constraints.
3. **Separate service per module:** independent scaling, but adds operational overhead with no demonstrated need. Rejected.

The user specified the direction, stack, product scope, and requested immediate implementation; the modular monolith is the implementation choice for this workspace.

## Architecture

Next.js serves a mobile-first PWA and same-origin JSON API. PostgreSQL is the source of truth. A worker container is reserved for scheduled work. Shared validation and domain helpers are used by HTTP routes and asynchronous paths. Local uploads live on a persistent volume. Caddy is an optional ingress profile; an existing Synology proxy can route to a configurable app port. Ollama and MCP are independently optional.

## What remains to implement

Implement a deployable core first: first-run owner/household setup, local login/session revocation, household-scoped persisted events/tasks/lists/meals/recipes/inventory/rewards, accessible dashboard and module navigation, PWA shell, Compose/Postgres/migrations, backups, and deployment docs. Extend other modules only where working end-to-end flows can be established. Keep a parity matrix and known limitations honest; a UI or table alone is not completion.
