# Synology deployment

1. Create a shared folder for the project and persistent data. Keep the data and backups access-controlled.
2. Copy the repository to the NAS or build the image on a computer with Docker, then transfer it for the NAS CPU architecture (the Python base supports common amd64 and arm64 architectures; verify your device first).
3. Copy `.env.example` to `.env`. The defaults use named persistent Docker volumes. Set `APP_URL` to the chosen HTTPS URL and pick a free host port.
4. For Synology Reverse Proxy, set `BIND_ADDRESS=0.0.0.0` and point the proxy to NAS port `HOST_PORT`; preserve Host and HTTPS scheme. Use a trusted certificate.
5. Or enable the included Caddy profile with `docker compose --profile caddy up -d --build`; configure DNS, use `https://householdsix.home.arpa:8443` by default, and install/trust the Caddy internal CA on devices. If changing the Caddy host port, update `APP_URL` to match.
6. Start the selected profile, inspect logs and health, then create the owner from a browser on the household LAN.
7. Do not forward public router ports. Confirm ports are unused before enabling the optional proxy.

For direct bind mounts, create the host data/backup folders and set ownership/permissions so the container's unprivileged `app` user can write. Named Docker volumes are the working default and avoid guessing NAS UIDs. Compose contains a single application service and optional Caddy; the requested PostgreSQL and worker services are not present because this alpha uses SQLite and has no scheduler.

This deployment path is documented but not validated against DSM or an actual NAS.
