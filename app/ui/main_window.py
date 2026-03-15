from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.indexer import Indexer
from app.core.search_service import SearchService
from app.db.database import ensure_db
from app.db.repository import Repository


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ArchiveSys MVP")
        self.resize(1000, 640)

        conn = ensure_db(Path("data/archive_sys.db"))
        repo = Repository(conn)
        self.indexer = Indexer(repo)
        self.search_service = SearchService(repo)

        central = QWidget(self)
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)

        controls = QHBoxLayout()
        self.source_label = QLabel("No source selected")
        self.pick_btn = QPushButton("Pick Source")
        self.index_btn = QPushButton("Index")
        self.pick_btn.clicked.connect(self.pick_source)
        self.index_btn.clicked.connect(self.index_source)
        controls.addWidget(self.source_label)
        controls.addWidget(self.pick_btn)
        controls.addWidget(self.index_btn)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search (FTS5)")
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.run_search)
        self.search_input.returnPressed.connect(self.run_search)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)

        self.results = QListWidget()

        root_layout.addLayout(controls)
        root_layout.addLayout(search_layout)
        root_layout.addWidget(self.results)

        self.selected_source: Path | None = None

    def pick_source(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select folder to index")
        if not selected:
            return
        self.selected_source = Path(selected)
        self.source_label.setText(str(self.selected_source))

    def index_source(self) -> None:
        if self.selected_source is None:
            QMessageBox.warning(self, "No source", "Please choose a source folder first.")
            return
        stats = self.indexer.index_source(self.selected_source)
        QMessageBox.information(
            self,
            "Index completed",
            f"Indexed: {stats['indexed']} files\nFailed: {stats['failed']} files",
        )

    def run_search(self) -> None:
        query = self.search_input.text()
        self.results.clear()
        for result in self.search_service.search(query):
            text = f"{result.filename}  ({result.ext or 'no-ext'})\n{result.path}"
            item = QListWidgetItem(text)
            self.results.addItem(item)


def run_app() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
