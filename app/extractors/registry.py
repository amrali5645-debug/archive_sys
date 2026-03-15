from __future__ import annotations

from pathlib import Path

from app.extractors.base import BaseExtractor, ExtractResult
from app.extractors.text_extractor import PlainTextExtractor


class ExtractorRegistry:
    def __init__(self) -> None:
        self.extractors: list[BaseExtractor] = [PlainTextExtractor()]

    def register(self, extractor: BaseExtractor) -> None:
        self.extractors.append(extractor)

    def extract(self, path: Path, mime: str) -> ExtractResult:
        for extractor in self.extractors:
            if extractor.can_handle(path, mime):
                return extractor.extract(path)
        return ExtractResult(text="", strategy="metadata_only")
