from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    enabled INTEGER NOT NULL DEFAULT 1,
    recursive INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    path TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    ext TEXT,
    mime TEXT,
    size INTEGER NOT NULL,
    sha256 TEXT,
    modified_at REAL NOT NULL,
    indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS contents (
    file_id INTEGER PRIMARY KEY,
    extracted_text TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(file_id) REFERENCES files(id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_index USING fts5(
    filename,
    path,
    combined_text,
    content=''
);
"""


def ensure_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn
