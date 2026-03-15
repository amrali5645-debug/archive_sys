from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal

from app.core.indexer import Indexer


class IndexWorkerSignals(QObject):
    progress = Signal(int, int, str)
    finished = Signal(dict)
    failed = Signal(str)


class IndexWorker(QRunnable):
    def __init__(self, indexer: Indexer, source: Path, recursive: bool = True) -> None:
        super().__init__()
        self.indexer = indexer
        self.source = source
        self.recursive = recursive
        self.signals = IndexWorkerSignals()
        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True

    def _should_stop(self) -> bool:
        return self._stop_requested

    def _on_progress(self, current: int, total: int, path: str) -> None:
        self.signals.progress.emit(current, total, path)

    def run(self) -> None:
        try:
            stats = self.indexer.index_source(
                self.source,
                recursive=self.recursive,
                progress_callback=self._on_progress,
                should_stop=self._should_stop,
            )
            self.signals.finished.emit(stats)
        except Exception as exc:  # noqa: BLE001
            self.signals.failed.emit(str(exc))
