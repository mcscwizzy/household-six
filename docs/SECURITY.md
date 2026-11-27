# Security

- Use only behind trusted HTTPS for LAN access. The default Compose bind is loopback.
- The service hashes passwords with scrypt and stores only a SHA-256 digest of random session IDs and CSRF tokens.
- Cookies are HttpOnly and SameSite=Strict, and are marked Secure when `APP_URL` is HTTPS.
- Mutations validate Origin and a session-bound CSRF value. Database lookups for household records include the authenticated household ID.
- Child point assignment is restricted; child completion is limited to their own or unassigned tasks. Display members are read-only.
- Login failures are delayed and temporarily throttled in process memory. This throttle is not shared across replicas and does not persist through restart.
- Static content uses a restrictive CSP. There is no file upload or remote URL fetch surface in this alpha.
- Containers drop Linux capabilities, use a non-root account, and mount the app filesystem read-only.

This implementation needs a professional security review before broad LAN exposure. There is no PostgreSQL RLS, persistent distributed rate limit, full role matrix, invitation flow, administrator reset flow, or device-management UI. Use unique household passwords, keep backups private, and restrict ingress at the reverse proxy/firewall.
