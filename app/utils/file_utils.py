from __future__ import annotations

import hashlib
from pathlib import Path


TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".xml",
    ".html",
    ".log",
    ".py",
    ".ini",
    ".yaml",
    ".yml",
}


def sha256_of_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def read_text_if_supported(path: Path, max_chars: int = 100_000) -> str:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return ""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        return content[:max_chars]
    except OSError:
        return ""
