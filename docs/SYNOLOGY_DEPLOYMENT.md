# Synology deployment guide

Household Six currently uses FastAPI/Uvicorn, SQLAlchemy, SQLite/WAL, additive Alembic migrations and a modular JavaScript client. Docker Compose runs the same web runtime. This guide describes a deployment procedure; the current branch has not been installed or accepted on a physical Synology NAS.

## Before installing

1. Confirm the NAS CPU architecture supports the pinned Python 3.12 Debian image and that the model (if enabled) fits available memory. The app container is limited to one CPU and 512 MB; the optional Ollama service is limited to two CPUs and 4 GB.
2. Create protected local NAS folders for app data and backups. Keep SQLite on the NAS's local filesystem, not an SMB/NFS mount. Restrict access to the data and backup folders.
3. Clone or copy the reviewed release candidate and pin the image or commit you intend to run. Create a private `.env` based on `.env.example` and set `DATA_PATH`, `BACKUP_PATH`, `HOST_PORT`, `BIND_ADDRESS`, `APP_URL` and `HOUSEHOLD_TIMEZONE`.
4. Keep AI and MCP disabled unless deliberately configured. Ollama is on the private Compose network and does not publish a host port. Do not expose database or model services.

## Trusted LAN access

The app binds to loopback by default. For Synology Reverse Proxy, configure DSM to terminate HTTPS with a trusted certificate, set `BIND_ADDRESS=0.0.0.0`, and proxy to the chosen `HOST_PORT`. Preserve the original Host and forwarded HTTPS scheme, and configure the app's `APP_URL` to the HTTPS origin. Verify Secure session cookies in a browser before creating household data.

The optional Caddy profile can serve trusted local HTTPS after household devices trust its local certificate. It is optional and can use a configurable HTTPS port. Follow [LOCAL_HTTPS.md](LOCAL_HTTPS.md). Do not forward public router ports or automatically change router/firewall configuration.

## Start and check

On a system with the Compose v2 plugin:

```sh
docker compose config
docker compose up -d --build household-six
docker compose ps
docker compose logs --tail=100 household-six
```

The baseline in this workspace was built with Docker Compose v1.29.2, using `docker-compose` commands, on a local Docker Engine. It reached healthy status, retained an authenticated completion after restart, and restored a synthetic database into a separate volume with SQLite integrity verified. Compose v2 and a physical NAS were not tested in this run.

The service uses a non-root user, read-only container filesystem, dropped capabilities, `no-new-privileges`, health check, restart policy, bounded CPU/memory, and rotated JSON logs. Persistent data and backups use separate named volumes by default. Review port and volume names before deploying alongside existing NAS applications.

## Backups, migrations and rollback

Schedule the instructions in [BACKUP_AND_RESTORE.md](BACKUP_AND_RESTORE.md) with DSM Task Scheduler, then copy protected backups to an independent location. Before an upgrade, stop writes, capture a backup, note the current image/commit and test restoration into a new disposable volume. Migrations are additive; retain the old image and a verified backup until the upgraded app is accepted. Never point a rollback at a database already modified by a newer schema without first restoring a compatible snapshot.

The restore evidence from this branch covered the SQLite database only. No uploaded-file store exists yet, so file and database snapshot coordination has not been exercised.

## Production readiness checklist

- Verify CPU architecture, local volume behavior, available memory, restart after DSM reboot and health status on the target NAS.
- Verify HTTPS trust and Secure cookies through the actual Synology Reverse Proxy on each household device.
- Configure scheduled backup, an independent protected copy, and a restore rehearsal.
- Review local firewall and proxy access; leave router port forwarding disabled.
- Complete the current security, feature and physical-device acceptance checklists before household production use.

No physical Synology, iPhone or iPad verification is claimed. The current continuation branch is not a final production release; see [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).
