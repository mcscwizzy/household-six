# Known limitations

- This is a runnable foundation, not the complete requested family operating system.
- Implementation uses Python 3.12 standard library and SQLite instead of Next.js/TypeScript, PostgreSQL/Drizzle and pnpm. The registry was unavailable during this run; no dependency installation or compatible-lockfile generation could be performed.
- Docker daemon access was denied, so Compose build/start, container health and NAS behavior remain unverified.
- There is no live multi-device event stream. Each view loads from the server when opened.
- Offline mode is limited to the static shell, locally cached last view, and best-effort queued task/list completion. Browser storage is not encrypted and sensitive records are not implemented.
- Calendar is a date label plus event list; no recurrence, timezone/DST policy, drag/drop, calendars, iCalendar, CalDAV or provider adapters exist.
- The application has no file upload, full-text search, attachments, push, maintenance jobs, worker, AI or MCP service.
- Icons are SVG-only. Dedicated PNG, Apple Touch, 192/512 and maskable raster exports have not been generated.
- The auth system is a small local implementation and needs independent security review before exposure beyond a trusted household LAN. The login throttle is per process and in-memory.
- Physical iPhone, iPad, Synology, certificate trust, push, performance and resource consumption were not tested.
