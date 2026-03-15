from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class SearchResult:
    path: str
    filename: str
    ext: str
    size: int


class Repository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert_source(self, path: str) -> int:
        self.conn.execute(
            """
            INSERT INTO sources(path) VALUES(?)
            ON CONFLICT(path) DO UPDATE SET enabled = 1
            """,
            (path,),
        )
        row = self.conn.execute("SELECT id FROM sources WHERE path = ?", (path,)).fetchone()
        self.conn.commit()
        return int(row[0])

    def upsert_file(
        self,
        source_id: int,
        path: str,
        filename: str,
        ext: str,
        mime: str,
        size: int,
        sha256: str,
        modified_at: float,
        extracted_text: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO files(source_id, path, filename, ext, mime, size, sha256, modified_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                source_id=excluded.source_id,
                filename=excluded.filename,
                ext=excluded.ext,
                mime=excluded.mime,
                size=excluded.size,
                sha256=excluded.sha256,
                modified_at=excluded.modified_at,
                indexed_at=CURRENT_TIMESTAMP
            """,
            (source_id, path, filename, ext, mime, size, sha256, modified_at),
        )
        file_id_row = self.conn.execute("SELECT id FROM files WHERE path = ?", (path,)).fetchone()
        file_id = int(file_id_row[0])

        self.conn.execute(
            """
            INSERT INTO contents(file_id, extracted_text)
            VALUES(?, ?)
            ON CONFLICT(file_id) DO UPDATE SET extracted_text=excluded.extracted_text
            """,
            (file_id, extracted_text),
        )

        self.conn.execute("DELETE FROM fts_index WHERE rowid = ?", (file_id,))
        self.conn.execute(
            "INSERT INTO fts_index(rowid, filename, path, combined_text) VALUES(?, ?, ?, ?)",
            (file_id, filename, path, f"{filename}\n{extracted_text}"),
        )
        self.conn.commit()

    def search(self, query: str, limit: int = 200) -> list[SearchResult]:
        rows = self.conn.execute(
            """
            SELECT files.path, files.filename, COALESCE(files.ext, ''), files.size
            FROM fts_index
            JOIN files ON files.id = fts_index.rowid
            WHERE fts_index MATCH ?
            ORDER BY bm25(fts_index)
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()

        return [SearchResult(path=r[0], filename=r[1], ext=r[2], size=int(r[3])) for r in rows]
