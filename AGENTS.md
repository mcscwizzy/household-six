# Household Six repository notes

- Keep household data local and do not add analytics or external identity dependencies.
- All reads and writes must include server-side household scoping. Treat the browser as untrusted.
- Validate request bodies, keep errors generic, and avoid logging identifiers or private content.
- Do not claim full feature parity or physical NAS/iPhone verification without evidence.
- The current dependency-free Python/SQLite service is a documented environment-driven deviation from the preferred TypeScript/PostgreSQL stack; do not silently introduce a second architecture.
- Run `python3 -m unittest discover -s tests -v` and `python3 -m compileall -q app tests scripts` after service changes.
