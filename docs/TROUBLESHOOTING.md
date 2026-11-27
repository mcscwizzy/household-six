# Troubleshooting

- **Can't open page:** confirm container health, local DNS, HTTPS certificate trust and configured port; the default app binds only to loopback.
- **Sign-in cookie does not persist:** use the same host each time and trusted HTTPS. If testing plain HTTP, set `APP_URL=http://...` only for local development.
- **Changes are not syncing:** check that the NAS is reachable. The offline queue only supports completing tasks/list entries and retries after a successful session refresh.
- **Backup restore refuses the target:** restore into a new empty directory and stop the app before swapping data.
- **Caddy certificate warning:** install and fully trust the Caddy internal CA on the device, or use a certificate trusted by that device.
- **Port already in use:** choose a different `HOST_PORT` or `CADDY_HTTPS_PORT`; do not change existing NAS services automatically.
- **Feature not found:** consult the status and parity docs; many of the requested modules are not yet implemented.
