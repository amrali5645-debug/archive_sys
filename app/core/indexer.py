from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Callable

from app.db.repository import Repository
from app.extractors.registry import ExtractorRegistry
from app.utils.file_utils import sha256_of_file

ProgressCallback = Callable[[int, int, str], None]
ShouldStopCallback = Callable[[], bool]


class Indexer:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository
        self.registry = ExtractorRegistry()

    def index_source(
        self,
        source_path: Path,
        recursive: bool = True,
        progress_callback: ProgressCallback | None = None,
        should_stop: ShouldStopCallback | None = None,
    ) -> dict[str, int]:
        source_id = self.repository.upsert_source(
            path=str(source_path.resolve()), name=source_path.name, recursive=recursive
        )
        job_id = self.repository.create_job(source_id)

        iterator = source_path.rglob("*") if recursive else source_path.glob("*")
        files = [p for p in iterator if p.is_file()]
        total = len(files)

        indexed = 0
        failed = 0

        for idx, item in enumerate(files, start=1):
            if should_stop and should_stop():
                self.repository.finish_job(job_id, indexed_count=indexed, failed_count=failed, status="stopped")
                return {"indexed": indexed, "failed": failed, "job_id": job_id, "total": total}

            try:
                stat = item.stat()
                mime, _ = mimetypes.guess_type(str(item))
                mime_final = mime or "application/octet-stream"
                extract_result = self.registry.extract(item, mime_final)

                self.repository.upsert_file(
                    source_id=source_id,
                    path=str(item.resolve()),
                    filename=item.name,
                    ext=item.suffix.lower(),
                    mime=mime_final,
                    size=stat.st_size,
                    sha256=sha256_of_file(item),
                    modified_at=stat.st_mtime,
                    extracted_text=extract_result.text,
                )
                indexed += 1
            except OSError as exc:
                failed += 1
                self.repository.add_error(stage="index", message=str(exc), file_path=str(item))

            if progress_callback:
                progress_callback(idx, total, str(item))

        self.repository.finish_job(job_id, indexed_count=indexed, failed_count=failed)
        return {"indexed": indexed, "failed": failed, "job_id": job_id, "total": total}
