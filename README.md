# Household Six

**Your household. Your hardware. Your data.**

Household Six is an independently developed, self-hosted household organizer. The local app includes a household calendar, chore and reward approvals, meal planning, shared shopping and pantry inventory, announcements, habits, allowance, a read-only display, household member administration, home maintenance and vehicle service records. Six and private MCP are optional.

See [implementation status](IMPLEMENTATION_STATUS.md) and the [feature matrix](docs/FEATURE_PARITY.md) for tested workflows and the remaining product backlog.

## Run locally

Requires Python 3.12 and the locked runtime dependencies.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
APP_URL=http://localhost:3000 python -m app.server
```

Visit <http://localhost:3000>. First-run setup creates the local owner. Use a unique password of at least 12 characters. For LAN use, put the app behind trusted HTTPS; do not expose the plain HTTP service to an untrusted network.

## Docker Compose

```sh
APP_URL=http://localhost:8088 docker compose up -d --build household-six
```

Open <http://localhost:8088> on the host. By default, Compose binds the app to `127.0.0.1:8088` and stores data in persistent Docker volumes. For the included local HTTPS proxy, set up local DNS for `householdsix.home.arpa`, then run:

```sh
docker compose --profile caddy up -d --build
```

Caddy serves on `https://householdsix.home.arpa:8443` by default using its internal certificate authority. Trust that CA on household devices as described in [local HTTPS](docs/LOCAL_HTTPS.md). If you change `CADDY_HTTPS_PORT`, update the port in `APP_URL` too. When using Synology Reverse Proxy instead, set `BIND_ADDRESS=0.0.0.0`, keep `HOST_PORT` unused, set `APP_URL` to the trusted HTTPS URL, and run:

```sh
docker compose up -d --build
```

The app is not published directly on the public internet. Change the host port if it conflicts with another NAS service. Configure data as a persistent Docker volume by default, or set `DATA_PATH` to a writable bind mount for direct Synology volume management.

## Backup

Stop the app for the simplest recovery process. The backup script also uses SQLite's online backup API for a consistent snapshot:

```sh
docker compose run --rm household-six python3 /app/scripts/backup.py
```

This writes into a persistent Docker volume. Export it to a protected NAS share with `docker compose cp household-six:/app/backups /volume1/household-six-backups` while the app container is running. DSM Task Scheduler can run the backup command daily. Set `BACKUP_PATH` to a host bind folder if desired, and ensure that folder is writable by the container's unprivileged `app` user.

Restore into a new data volume to preserve the current copy:

```sh
docker compose stop household-six
DATA_PATH=household-six-restore-data docker compose run --rm household-six python3 /app/scripts/restore.py /app/backups/household-six-<timestamp>.tar.gz
```

After validating the restored volume, set `DATA_PATH=household-six-restore-data` in `.env` and start the app again. Backups contain household records and password hashes. Keep them private and encrypt them at rest using the NAS's protected backup target. See [backup and restore](docs/BACKUP_AND_RESTORE.md).

## Development checks

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q app tests scripts
node --check app/static/app.js
```

Run loopback HTTP tests on a host that permits local sockets:

```sh
HOUSEHOLD_SIX_LIVE=1 python3 -m unittest discover -s tests -v
```

The Playwright suite needs installed Chromium and WebKit browsers plus a local server configured with an HTTP `APP_URL`:

```sh
npm ci
APP_URL=http://127.0.0.1:3000 DATA_DIR=/tmp/household-six-e2e \
  BIND_ADDRESS=127.0.0.1 APP_PORT=3000 python3 -m app.server
npm run test:e2e
```

The checked-in Compose smoke script creates synthetic data, then verifies session and database persistence across a container restart. Run it only with a disposable project and data volume. See [testing](docs/TESTING.md).

## Architecture note

Uvicorn serves the FastAPI application. SQLAlchemy configures local SQLite connections with WAL, and Alembic applies the original additive migrations and tracks new ones. Set `DATA_PATH` to a volume backed by local NAS storage.

`requirements.lock` pins and hashes the runtime dependency tree for Python 3.12. `requirements-optional.lock` also includes the MCP SDK. Browser test dependencies are installed with `npm ci`. Set `HOUSEHOLD_SIX_LIVE=1` when running the test suite on a machine that can bind a loopback socket.

The v1.0 release candidate has not been prepared. Invitations, parent PIN/shared-device switching, secure household document storage, emergency records, budgeting, devotional and prayer tracking, photo albums, a durable general reminder scheduler, expanded offline viewing and several planner/calendar integrations remain incomplete. Physical NAS and iPhone acceptance have not been performed. Do not treat the current branch as a production release.

See [implementation status](IMPLEMENTATION_STATUS.md), [known limitations](docs/KNOWN_LIMITATIONS.md), [architecture](docs/ARCHITECTURE.md), and [ADR 0001](docs/adr/0001-approved-runtime-and-data-store.md).
