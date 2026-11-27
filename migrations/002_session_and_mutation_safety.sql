ALTER TABLE users ADD COLUMN disabled_at TEXT;

CREATE TABLE mutation_receipts (
  household_id TEXT NOT NULL REFERENCES households(id) ON DELETE CASCADE,
  mutation_id TEXT NOT NULL,
  actor_id TEXT NOT NULL REFERENCES users(id),
  operation TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  result_version INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (household_id, mutation_id)
);

CREATE INDEX mutation_receipts_actor_created
  ON mutation_receipts(household_id, actor_id, created_at);
