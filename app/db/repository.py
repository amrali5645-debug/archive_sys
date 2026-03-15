from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class SearchResult:
    path: str
    filename: str
    ext: str
    size: int
    source_path: str


@dataclass
class SourceRecord:
    id: int
    name: str
    path: str
    enabled: bool
    recursive: bool


@dataclass
class JobRecord:
    id: int
    source_id: int | None
    status: str
    indexed_count: int
    failed_count: int
    started_at: str
    finished_at: str | None


@dataclass
class ErrorRecord:
    stage: str
    file_path: str
    message: str
    created_at: str


@dataclass
class DashboardStats:
    total_sources: int
    total_files: int
    total_jobs: int
    total_errors: int
    last_job_status: str
    last_job_started_at: str


class Repository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert_source(self, path: str, name: str | None = None, recursive: bool = True) -> int:
        self.conn.execute(
            """
            INSERT INTO sources(name, path, recursive) VALUES(?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET enabled = 1, recursive = excluded.recursive
            """,
            (name, path, 1 if recursive else 0),
        )
        row = self.conn.execute("SELECT id FROM sources WHERE path = ?", (path,)).fetchone()
        self.conn.commit()
        return int(row[0])

    def list_sources(self) -> list[SourceRecord]:
        rows = self.conn.execute(
            "SELECT id, COALESCE(name, ''), path, enabled, recursive FROM sources ORDER BY created_at DESC"
        ).fetchall()
        return [
            SourceRecord(id=int(r[0]), name=r[1], path=r[2], enabled=bool(r[3]), recursive=bool(r[4]))
            for r in rows
        ]

    def set_source_enabled(self, source_id: int, enabled: bool) -> None:
        self.conn.execute("UPDATE sources SET enabled = ? WHERE id = ?", (1 if enabled else 0, source_id))
        self.conn.commit()

    def create_job(self, source_id: int | None) -> int:
        cur = self.conn.execute(
            "INSERT INTO jobs(source_id, status) VALUES(?, 'running')",
            (source_id,),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def finish_job(self, job_id: int, indexed_count: int, failed_count: int, status: str = "done") -> None:
        self.conn.execute(
            """
            UPDATE jobs
            SET status = ?, indexed_count = ?, failed_count = ?, finished_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, indexed_count, failed_count, job_id),
        )
        self.conn.commit()

    def recent_jobs(self, limit: int = 20) -> list[JobRecord]:
        rows = self.conn.execute(
            """
            SELECT id, source_id, status, indexed_count, failed_count, started_at, finished_at
            FROM jobs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            JobRecord(
                id=int(r[0]),
                source_id=(int(r[1]) if r[1] is not None else None),
                status=r[2],
                indexed_count=int(r[3]),
                failed_count=int(r[4]),
                started_at=r[5],
                finished_at=r[6],
            )
            for r in rows
        ]

    def add_error(self, stage: str, message: str, file_path: str = "") -> None:
        self.conn.execute(
            "INSERT INTO errors(file_path, stage, message) VALUES(?, ?, ?)",
            (file_path, stage, message),
        )
        self.conn.commit()

    def recent_errors(self, limit: int = 50) -> list[ErrorRecord]:
        rows = self.conn.execute(
            "SELECT stage, COALESCE(file_path, ''), message, created_at FROM errors ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [ErrorRecord(stage=r[0], file_path=r[1], message=r[2], created_at=r[3]) for r in rows]

    def get_dashboard_stats(self) -> DashboardStats:
        total_sources = int(self.conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0])
        total_files = int(self.conn.execute("SELECT COUNT(*) FROM files").fetchone()[0])
        total_jobs = int(self.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0])
        total_errors = int(self.conn.execute("SELECT COUNT(*) FROM errors").fetchone()[0])
        last_job = self.conn.execute(
            "SELECT COALESCE(status, ''), COALESCE(started_at, '') FROM jobs ORDER BY id DESC LIMIT 1"
        ).fetchone()

        return DashboardStats(
            total_sources=total_sources,
            total_files=total_files,
            total_jobs=total_jobs,
            total_errors=total_errors,
            last_job_status=(last_job[0] if last_job else ""),
            last_job_started_at=(last_job[1] if last_job else ""),
        )

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

    def search(self, query: str, ext_filter: str = "", source_filter: str = "", limit: int = 200) -> list[SearchResult]:
        sql = """
            SELECT files.path, files.filename, COALESCE(files.ext, ''), files.size, sources.path
            FROM fts_index
            JOIN files ON files.id = fts_index.rowid
            JOIN sources ON sources.id = files.source_id
            WHERE fts_index MATCH ?
        """
        args: list[object] = [query]

        if ext_filter:
            sql += " AND files.ext = ?"
            args.append(ext_filter.lower())

        if source_filter:
            sql += " AND sources.path = ?"
            args.append(source_filter)

        sql += " ORDER BY bm25(fts_index) LIMIT ?"
        args.append(limit)

        rows = self.conn.execute(sql, tuple(args)).fetchall()
        return [
            SearchResult(path=r[0], filename=r[1], ext=r[2], size=int(r[3]), source_path=r[4])
            for r in rows
        ]

    def get_content_preview(self, path: str, max_chars: int = 1200) -> str:
        row = self.conn.execute(
            """
            SELECT substr(contents.extracted_text, 1, ?)
            FROM contents
            JOIN files ON files.id = contents.file_id
            WHERE files.path = ?
            """,
            (max_chars, path),
        ).fetchone()
        return row[0] if row and row[0] else ""
