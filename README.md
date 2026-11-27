# Household Six

**Your household. Your hardware. Your data.**

Household Six is an independently developed, self-hosted household organizer. This repository currently contains an early, runnable private alpha with local authentication, household-scoped SQLite persistence, a responsive installable web shell, and working shared lists for tasks, events, meals, shopping, recipes, inventory, rewards, and announcements.

This is not a completed substitute for every feature in Skylight Calendar. The implementation status and platform limits are in [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) and [docs/FEATURE_PARITY.md](docs/FEATURE_PARITY.md).

## Run locally

Requires Python 3.12 or newer. No Python packages are required.

```sh
mkdir -p data
BIND_ADDRESS=127.0.0.1 APP_URL=http://localhost:3000 APP_PORT=3000 DATA_DIR=./data python3 -m app.server
```

Visit <http://localhost:3000>. First-run setup creates the local owner. Use a unique password of at least 12 characters. For LAN use, put the app behind trusted HTTPS; do not expose the plain HTTP service to an untrusted network.

## Docker Compose

```sh
cp .env.example .env
mkdir -p data
docker compose up -d --build
```

By default, Compose binds the app to `127.0.0.1:8088` and stores data in persistent Docker volumes. For the included local HTTPS proxy, set up local DNS for `householdsix.home.arpa`, then run:

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

## Architecture note

The approved continuation architecture is Python 3.12+, FastAPI/Uvicorn, SQLite/WAL, SQLAlchemy/Alembic, modular JavaScript, IndexedDB, household-scoped SSE and optional local Ollama/MCP. The current alpha still uses Python's standard-library HTTP server and `sqlite3`: package lookup failed from this environment, and the FastAPI stack has not been installed or verified. The application therefore remains runnable without dependencies, but the target server and ORM architecture are incomplete. See [ADR 0001](docs/adr/0001-approved-runtime-and-data-store.md) for the decision and exact environment evidence.

The approved target's direct runtime and optional MCP package versions are pinned in `requirements.txt` and `requirements-optional.txt`. In a registry-enabled environment, install them inside a virtual environment with `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`. Add optional MCP only when building that feature. A transitive lockfile could not be generated here because PyPI resolution is unavailable; these packages are not required by the current alpha.

See [implementation status](IMPLEMENTATION_STATUS.md), [known limitations](docs/KNOWN_LIMITATIONS.md), [architecture](docs/ARCHITECTURE.md), and [ADR 0001](docs/adr/0001-approved-runtime-and-data-store.md).
