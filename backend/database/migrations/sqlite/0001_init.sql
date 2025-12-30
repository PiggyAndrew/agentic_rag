CREATE TABLE IF NOT EXISTS knowledge_bases (
  kb_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NULL,
  created_at_ms INTEGER NOT NULL,
  updated_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_files (
  kb_id INTEGER NOT NULL,
  file_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  created_at_ms INTEGER NOT NULL,
  updated_at_ms INTEGER NOT NULL,
  chunk_count INTEGER NOT NULL,
  status TEXT NOT NULL,
  source_path TEXT NULL,
  PRIMARY KEY (kb_id, file_id),
  FOREIGN KEY (kb_id) REFERENCES knowledge_bases(kb_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_knowledge_files_kb_id ON knowledge_files(kb_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_files_name ON knowledge_files(name);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
  kb_id INTEGER NOT NULL,
  file_id INTEGER NOT NULL,
  chunk_index INTEGER NOT NULL,
  content TEXT NOT NULL,
  metadata_json TEXT NULL,
  created_at_ms INTEGER NOT NULL,
  updated_at_ms INTEGER NOT NULL,
  PRIMARY KEY (kb_id, file_id, chunk_index),
  FOREIGN KEY (kb_id) REFERENCES knowledge_bases(kb_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_kb_file ON knowledge_chunks(kb_id, file_id);
