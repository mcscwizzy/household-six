# Security

- Use only behind trusted HTTPS for LAN access. The default Compose bind is loopback.
- The service hashes passwords with scrypt and stores only a SHA-256 digest of random session IDs and CSRF tokens.
- Cookies are HttpOnly and SameSite=Strict, and are marked Secure when `APP_URL` is HTTPS.
- Mutations validate Origin and a session-bound CSRF value. Database lookups for household records include the authenticated household ID.
- Child point assignment is restricted; child completion is limited to their own or unassigned tasks. Display members are read-only.
- Only the owner can add an administrator. Administrators can add adult, child and display profiles; ordinary adults, children and display sessions cannot create members. This rule is enforced by the service as well as reflected in the form.
- Completion writes require a positive expected item version and a bounded unique mutation ID. A stale version returns a conflict; an exact replay is bound to household, actor, operation and entity through a receipt.
- Offline policy is default-deny for records: no household cache is stored in localStorage or IndexedDB. IndexedDB is limited to task completion intents keyed to the active member. An offline reload is signed out; these intents are not a strong encryption boundary and cannot guarantee revocation while disconnected.
- Session lookup rejects disabled accounts, and detectable revocation clears the current member's queued intents. A disable-account management flow is not yet implemented.
- Login failures are delayed and temporarily throttled in process memory. This throttle is not shared across replicas and does not persist through restart.
- Static content uses a restrictive CSP. There is no file upload or remote URL fetch surface in this alpha.
- Containers drop Linux capabilities, use a non-root account, and mount the app filesystem read-only.

This implementation needs a professional security review before broad LAN exposure. There is no PostgreSQL RLS, persistent distributed rate limit, full role matrix, invitation flow, administrator reset flow, or device-management UI. Use unique household passwords, keep backups private, and restrict ingress at the reverse proxy/firewall.
