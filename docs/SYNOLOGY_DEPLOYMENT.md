# Synology deployment

The existing Dockerfile and Compose file still launch the standard-library alpha. The approved FastAPI/Uvicorn runtime migration is incomplete, and Compose cannot be validated in this workspace because the Docker Compose plugin is absent. Do not treat these instructions as NAS verification.

## Current alpha setup

1. Create a protected local shared folder for the project and persistent data. Do not place the active SQLite database on SMB/NFS.
2. Copy the repository to the NAS or build the image on a compatible amd64/arm64 machine.
3. Copy `.env.example` to `.env`; set `APP_URL` to the trusted HTTPS URL and choose an unused host port. The checked-in runtime does not yet consume the AI/MCP options in the example.
4. For Synology Reverse Proxy, use a trusted certificate, set `BIND_ADDRESS=0.0.0.0`, and route to `HOST_PORT`. Preserve the original Host and HTTPS scheme.
5. Or configure local DNS for `householdsix.home.arpa` and use the optional Caddy profile. Trust its internal certificate only on household devices, as described in [LOCAL_HTTPS.md](LOCAL_HTTPS.md).
6. Start with `docker compose up -d --build`, inspect health and logs, then create the first household on the local network.
7. Do not forward public router ports. Do not modify firewall settings automatically.

Defaults bind the app to loopback and use persistent Docker volumes. Keep the NAS installation restricted to trusted local ingress. The current alpha offers SQLite backup/restore scripts; uploaded files/configuration are not part of backups because those modules do not exist yet.

## Required verification before household deployment

- Run the Compose CI test against the actual Compose version and confirm health, authenticated create/complete operations, and data persistence after restart.
- Restore a backup into a disposable empty volume and verify IDs, sessions, items and ledger integrity before switching any live path.
- Verify the actual NAS model, local filesystem, HTTPS certificate trust, architecture and memory/CPU limits.
- Keep an independent protected backup and the prior app image/database until the upgrade is accepted.

No DSM/NAS, physical iPhone/iPad, local DNS or trusted certificate verification is claimed.
