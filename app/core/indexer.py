from __future__ import annotations

import mimetypes
from pathlib import Path

from app.db.repository import Repository
from app.utils.file_utils import read_text_if_supported, sha256_of_file


class Indexer:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def index_source(self, source_path: Path, recursive: bool = True) -> dict[str, int]:
        source_id = self.repository.upsert_source(str(source_path.resolve()))

        indexed = 0
        failed = 0

        iterator = source_path.rglob("*") if recursive else source_path.glob("*")
        for item in iterator:
            if not item.is_file():
                continue
            try:
                stat = item.stat()
                mime, _ = mimetypes.guess_type(str(item))
                self.repository.upsert_file(
                    source_id=source_id,
                    path=str(item.resolve()),
                    filename=item.name,
                    ext=item.suffix.lower(),
                    mime=mime or "application/octet-stream",
                    size=stat.st_size,
                    sha256=sha256_of_file(item),
                    modified_at=stat.st_mtime,
                    extracted_text=read_text_if_supported(item),
                )
                indexed += 1
            except OSError:
                failed += 1

        return {"indexed": indexed, "failed": failed}
