PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS households (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, timezone TEXT NOT NULL DEFAULT 'America/Chicago', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id) ON DELETE CASCADE,
  username TEXT NOT NULL COLLATE NOCASE, password_hash TEXT NOT NULL, display_name TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('owner','admin','adult','child','display')),
  color TEXT NOT NULL DEFAULT '#78937D', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(username)
);
CREATE TABLE IF NOT EXISTS sessions (
  id_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  csrf_hash TEXT NOT NULL, expires_at TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS csrf_tokens (
  session_id_hash TEXT NOT NULL REFERENCES sessions(id_hash) ON DELETE CASCADE,
  token_hash TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY(session_id_hash,token_hash)
);
CREATE TABLE IF NOT EXISTS items (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK(kind IN ('event','task','shopping','meal','inventory','recipe','announcement','reward')),
  title TEXT NOT NULL, details TEXT NOT NULL DEFAULT '', due_at TEXT, assigned_to TEXT,
  completed INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0,1)), value INTEGER NOT NULL DEFAULT 0,
  idempotency_key TEXT, version INTEGER NOT NULL DEFAULT 1, created_by TEXT NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(household_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS items_household_kind_due ON items(household_id,kind,due_at);
CREATE TABLE IF NOT EXISTS points_ledger (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id) ON DELETE CASCADE,
  member_id TEXT NOT NULL REFERENCES users(id), item_id TEXT NOT NULL REFERENCES items(id),
  amount INTEGER NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(item_id, reason)
);
CREATE TABLE IF NOT EXISTS audit_log (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id) ON DELETE CASCADE,
  actor_id TEXT NOT NULL REFERENCES users(id), action TEXT NOT NULL, object_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
