from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExtractResult:
    text: str
    strategy: str


class BaseExtractor:
    name = "base"

    def can_handle(self, path: Path, mime: str) -> bool:
        raise NotImplementedError

    def extract(self, path: Path) -> ExtractResult:
        raise NotImplementedError
