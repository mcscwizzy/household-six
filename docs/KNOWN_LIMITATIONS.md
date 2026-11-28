# Known limitations

- Calendar imports support daily through yearly recurrence and skipped dates. Recurrence overrides and some advanced iCalendar rules need additional support. CalDAV, external calendar providers and reminder delivery remain on the backlog.
- Today shows overdue recurring chores from the past 30 days. Older occurrences remain available on the dated chore board. History lists show the most recent entries.
- The service uses a single Uvicorn process with household-scoped SSE. The browser refetches after reconnecting. Persistent event replay and multi-process delivery remain open.
- The PWA stores only the static shell and member-keyed completion intents. It requires explicit online authentication after an offline reload. Disconnected devices cannot receive server-side session revocations.
- Account administration now includes profile name/color/avatar, disable/reactivate, administrator-assisted reset and session listing/revocation. Parent PIN setup, managed child profiles, invitations, shared-device profile switching and expanded authentication rate limits remain unfinished. Login throttling is process-local and resets on restart.
- Maintenance and vehicle modules cover scheduled work, service history, costs and adult Today reminders. They do not yet include attached files, a general notification scheduler, mileage-triggered job execution or dedicated tire/battery workflows.
- The rest of the product backlog includes maintenance, vehicles, devotional and prayer tracking, document storage, emergency information, budgeting, photos and local notifications. See [feature parity](FEATURE_PARITY.md).
- Six handles selected local actions and requires approval for writes. Model quality varies by prompt, attachment and hardware. The private MCP server supports scoped stdio reads and an optional grocery proposal.
- The local restore drill used synthetic data in an isolated volume. It verified the database only; the app has no uploaded-file store yet. Physical Synology, LAN HTTPS, iPhone and iPad installation still need device verification.
- This continuation does not complete Operation Homefront or constitute a v1.0 release candidate. Financial, emergency, document, devotional, photo, durable notification, expanded offline, provider-sync and multiple planner requirements remain open.
