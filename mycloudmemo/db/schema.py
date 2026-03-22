"""SQLite schema definitions for MyCloudMemo."""

from __future__ import annotations

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

-- Folders table (unchanged - still hierarchical)
CREATE TABLE IF NOT EXISTS folders (
    id TEXT PRIMARY KEY,
    parent_id TEXT REFERENCES folders(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_folders_parent_id ON folders(parent_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_folders_parent_name
    ON folders(parent_id, name);
CREATE INDEX IF NOT EXISTS idx_folders_parent_order ON folders(parent_id, sort_order);

-- Memos table - stores metadata only, content is in .md files
CREATE TABLE IF NOT EXISTS memos (
    id TEXT PRIMARY KEY,
    folder_id TEXT NOT NULL REFERENCES folders(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    file_name TEXT NOT NULL,  -- Relative path like "notes/2024/memo_abc123.md"
    is_synced INTEGER NOT NULL DEFAULT 0,  -- 0 = dirty, 1 = synced
    last_modified TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_memos_folder_id ON memos(folder_id);
CREATE INDEX IF NOT EXISTS idx_memos_synced ON memos(is_synced, last_modified);

-- Root folder
INSERT OR IGNORE INTO folders (id, parent_id, name)
VALUES ('root', NULL, 'Notes');
"""
