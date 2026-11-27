# Known limitations

- Calendar imports support daily through yearly recurrence and skipped dates. Recurrence overrides and some advanced iCalendar rules need additional support. CalDAV, external calendar providers and reminder delivery remain on the backlog.
- Today shows overdue recurring chores from the past 30 days. Older occurrences remain available on the dated chore board. History lists show the most recent entries.
- The service uses a single Uvicorn process with household-scoped SSE. The browser refetches after reconnecting. Persistent event replay and multi-process delivery remain open.
- The PWA stores only the static shell and member-keyed completion intents. It requires explicit online authentication after an offline reload. Disconnected devices cannot receive server-side session revocations.
- Local account administration still needs account disable and reset screens, session management, parent PIN and additional rate-limit coverage.
- The rest of the product backlog includes habits, allowance, maintenance, vehicles, devotional and prayer tracking, document storage, emergency information, budgeting, photos and local notifications. See [feature parity](FEATURE_PARITY.md).
- Six handles selected local actions and requires approval for writes. Model quality varies by prompt, attachment and hardware. The private MCP server supports scoped stdio reads and an optional grocery proposal.
- The local restore drill used synthetic data in an isolated volume. Physical Synology, LAN HTTPS, iPhone and iPad installation still need device verification.
