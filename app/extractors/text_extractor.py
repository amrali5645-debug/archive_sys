from __future__ import annotations

from pathlib import Path

from app.extractors.base import BaseExtractor, ExtractResult


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


class PlainTextExtractor(BaseExtractor):
    name = "plain_text"

    def can_handle(self, path: Path, mime: str) -> bool:
        return path.suffix.lower() in TEXT_EXTENSIONS or mime.startswith("text/")

    def extract(self, path: Path) -> ExtractResult:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        return ExtractResult(text=text[:100_000], strategy=self.name)
