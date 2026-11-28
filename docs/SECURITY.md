# Security

- Use only behind trusted HTTPS for LAN access. The default Compose bind is loopback.
- The service hashes passwords with scrypt and stores only a SHA-256 digest of random session IDs and CSRF tokens.
- Cookies are HttpOnly and SameSite=Strict, and are marked Secure when `APP_URL` is HTTPS.
- Mutations validate Origin and a session-bound CSRF value. Database lookups for household records include the authenticated household ID.
- Server permissions are declared for owner, administrator, adult, child and display roles. The child role has a deliberately narrow set of chore, shopping, reward and personal routine actions; display accounts have read-only display surfaces. Sensitive modules are not yet implemented just because their future permissions are declared.
- Only the owner can add an administrator. Administrators can add adult, child and display profiles; ordinary adults, children and display sessions cannot create members. This rule is enforced by the service as well as reflected in the form.
- Completion writes require a positive expected item version and a bounded unique mutation ID. A stale version returns a conflict; an exact replay is bound to household, actor, operation and entity through a receipt.
- Offline policy is default-deny for records: no household cache is stored in localStorage or IndexedDB. IndexedDB is limited to task completion intents keyed to the active member. An offline reload is signed out; these intents are not a strong encryption boundary and cannot guarantee revocation while disconnected.
- Profile edits, disable/reactivate, assisted password reset, member session listing and session revocation are household-scoped. Only owner/admin can manage another member; admins cannot manage owner accounts. Disabling or resetting a password revokes that member's sessions. Disabled accounts are rejected at session lookup.
- Self-service session listing/revocation and owner/admin member-session listing/revocation are available. There is no parent PIN, invitation, managed-child profile or secure shared-device switching flow. Session revocation cannot reach an already disconnected device until it reconnects.
- Login failures are delayed and temporarily throttled in process memory. This throttle is not shared across replicas and does not persist through restart; the new account-management endpoints do not have a separate persistent rate limiter.
- Static content uses a restrictive CSP. There is no file upload or remote URL fetch surface in this branch. Household documents and emergency records are not implemented.
- Containers drop Linux capabilities, use a non-root account, and mount the app filesystem read-only.

This implementation needs a professional security review before broad LAN exposure. Automated checks do not establish zero vulnerabilities. There is no PostgreSQL RLS, persistent distributed rate limiter, invitation flow, parent PIN or trusted-device profile switching. Use unique household passwords, keep backups private, and restrict ingress at the reverse proxy/firewall.
