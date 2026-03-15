from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.indexer import Indexer
from app.core.search_service import SearchService
from app.db.database import ensure_db
from app.db.repository import Repository
from app.workers.index_worker import IndexWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("أرشيف سيستم - النسخة الأولية المتقدمة")
        self.resize(1240, 780)

        conn = ensure_db(Path("data/archive_sys.db"))
        self.repo = Repository(conn)
        self.indexer = Indexer(self.repo)
        self.search_service = SearchService(self.repo)

        self.thread_pool = QThreadPool.globalInstance()
        self.active_worker: IndexWorker | None = None

        tabs = QTabWidget(self)
        self.setCentralWidget(tabs)

        tabs.addTab(self._build_dashboard_tab(), "لوحة التحكم")
        tabs.addTab(self._build_search_tab(), "البحث")
        tabs.addTab(self._build_sources_tab(), "المصادر")
        tabs.addTab(self._build_jobs_tab(), "الوظائف والسجل")

        self.refresh_sources()
        self.refresh_jobs_and_errors()
        self.refresh_dashboard()

    def _build_dashboard_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("ملخص تنفيذي لحالة النظام")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        card = QGroupBox("المؤشرات الحالية")
        grid = QGridLayout(card)

        self.kpi_sources = QLabel("0")
        self.kpi_files = QLabel("0")
        self.kpi_jobs = QLabel("0")
        self.kpi_errors = QLabel("0")
        self.kpi_last_job = QLabel("-")

        grid.addWidget(QLabel("عدد المصادر"), 0, 0)
        grid.addWidget(self.kpi_sources, 0, 1)

        grid.addWidget(QLabel("عدد الملفات المفهرسة"), 1, 0)
        grid.addWidget(self.kpi_files, 1, 1)

        grid.addWidget(QLabel("عدد وظائف الفهرسة"), 2, 0)
        grid.addWidget(self.kpi_jobs, 2, 1)

        grid.addWidget(QLabel("عدد الأخطاء"), 3, 0)
        grid.addWidget(self.kpi_errors, 3, 1)

        grid.addWidget(QLabel("آخر وظيفة"), 4, 0)
        grid.addWidget(self.kpi_last_job, 4, 1)

        self.refresh_dashboard_btn = QPushButton("تحديث المؤشرات")
        self.refresh_dashboard_btn.clicked.connect(self.refresh_dashboard)

        layout.addWidget(title)
        layout.addWidget(card)
        layout.addWidget(self.refresh_dashboard_btn)
        layout.addStretch(1)
        return page

    def _build_search_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        form_box = QGroupBox("بحث شامل")
        form = QFormLayout(form_box)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("اكتب عبارة البحث...")
        self.search_input.returnPressed.connect(self.run_search)

        self.ext_filter = QComboBox()
        self.ext_filter.addItems(["الكل", ".txt", ".md", ".csv", ".json", ".xml", ".html", ".py"])

        self.source_filter = QComboBox()
        self.source_filter.addItem("كل المصادر")

        self.search_btn = QPushButton("بحث")
        self.search_btn.clicked.connect(self.run_search)

        form.addRow("الاستعلام", self.search_input)
        form.addRow("نوع الملف", self.ext_filter)
        form.addRow("المصدر", self.source_filter)
        form.addRow(self.search_btn)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.results = QListWidget()
        self.results.currentItemChanged.connect(self.show_preview)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("معاينة المحتوى المستخرج ستظهر هنا")

        splitter.addWidget(self.results)
        splitter.addWidget(self.preview)
        splitter.setSizes([550, 650])

        layout.addWidget(form_box)
        layout.addWidget(splitter)
        return page

    def _build_sources_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        controls = QHBoxLayout()
        self.source_label = QLabel("لم يتم اختيار مصدر")
        self.pick_btn = QPushButton("اختيار مجلد")
        self.pick_btn.clicked.connect(self.pick_source)

        self.recursive_cb = QCheckBox("يشمل المجلدات الفرعية")
        self.recursive_cb.setChecked(True)

        self.index_btn = QPushButton("بدء الفهرسة")
        self.index_btn.clicked.connect(self.index_source_async)

        self.stop_btn = QPushButton("إيقاف")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_indexing)

        controls.addWidget(self.source_label)
        controls.addWidget(self.pick_btn)
        controls.addWidget(self.recursive_cb)
        controls.addWidget(self.index_btn)
        controls.addWidget(self.stop_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_status = QLabel("الحالة: جاهز")

        self.sources_list = QListWidget()

        layout.addLayout(controls)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_status)
        layout.addWidget(QLabel("المصادر المسجلة:"))
        layout.addWidget(self.sources_list)

        self.selected_source: Path | None = None
        return page

    def _build_jobs_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        row = QHBoxLayout()
        self.refresh_btn = QPushButton("تحديث")
        self.refresh_btn.clicked.connect(self.refresh_jobs_and_errors)
        row.addWidget(self.refresh_btn)
        row.addStretch(1)

        self.jobs_list = QListWidget()
        self.errors_list = QListWidget()

        layout.addLayout(row)
        layout.addWidget(QLabel("آخر مهام الفهرسة"))
        layout.addWidget(self.jobs_list)
        layout.addWidget(QLabel("آخر الأخطاء"))
        layout.addWidget(self.errors_list)
        return page

    def pick_source(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "اختر المجلد المراد فهرسته")
        if not selected:
            return
        self.selected_source = Path(selected)
        self.source_label.setText(str(self.selected_source))

    def index_source_async(self) -> None:
        if self.active_worker is not None:
            QMessageBox.information(self, "معلومة", "هناك مهمة فهرسة قيد التنفيذ بالفعل")
            return

        if self.selected_source is None:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار مصدر أولاً")
            return

        recursive = self.recursive_cb.isChecked()
        worker = IndexWorker(self.indexer, self.selected_source, recursive=recursive)
        worker.signals.progress.connect(self.on_index_progress)
        worker.signals.finished.connect(self.on_index_finished)
        worker.signals.failed.connect(self.on_index_failed)

        self.active_worker = worker
        self.index_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_status.setText("الحالة: جاري الفهرسة...")

        self.thread_pool.start(worker)

    def stop_indexing(self) -> None:
        if self.active_worker is None:
            return
        self.active_worker.request_stop()
        self.progress_status.setText("الحالة: جاري إرسال طلب الإيقاف...")

    def on_index_progress(self, current: int, total: int, path: str) -> None:
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))
        self.progress_status.setText(f"الحالة: {current}/{total} | {path}")

    def on_index_finished(self, stats: dict) -> None:
        self.active_worker = None
        self.index_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(100)

        QMessageBox.information(
            self,
            "اكتملت الفهرسة",
            f"رقم الوظيفة: {stats['job_id']}\nتمت فهرسة: {stats['indexed']}\nفشل: {stats['failed']}",
        )
        self.progress_status.setText("الحالة: اكتملت")
        self.refresh_sources()
        self.refresh_jobs_and_errors()
        self.refresh_dashboard()

    def on_index_failed(self, message: str) -> None:
        self.active_worker = None
        self.index_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_status.setText("الحالة: فشل")
        QMessageBox.critical(self, "خطأ", f"فشلت الفهرسة: {message}")

    def refresh_sources(self) -> None:
        sources = self.repo.list_sources()
        self.sources_list.clear()

        self.source_filter.blockSignals(True)
        self.source_filter.clear()
        self.source_filter.addItem("كل المصادر")

        for src in sources:
            text = f"{src.name or '(بدون اسم)'} | {src.path} | recursive={src.recursive}"
            self.sources_list.addItem(QListWidgetItem(text))
            self.source_filter.addItem(src.path)

        self.source_filter.blockSignals(False)

    def refresh_dashboard(self) -> None:
        stats = self.repo.get_dashboard_stats()
        self.kpi_sources.setText(str(stats.total_sources))
        self.kpi_files.setText(str(stats.total_files))
        self.kpi_jobs.setText(str(stats.total_jobs))
        self.kpi_errors.setText(str(stats.total_errors))

        if stats.last_job_status:
            self.kpi_last_job.setText(f"{stats.last_job_status} | {stats.last_job_started_at}")
        else:
            self.kpi_last_job.setText("لا توجد وظائف بعد")

    def run_search(self) -> None:
        query = self.search_input.text()
        self.results.clear()
        self.preview.clear()

        ext = self.ext_filter.currentText()
        ext_filter = "" if ext == "الكل" else ext

        src = self.source_filter.currentText()
        source_filter = "" if src == "كل المصادر" else src

        for result in self.search_service.search(query, ext_filter=ext_filter, source_filter=source_filter):
            text = (
                f"{result.filename} ({result.ext or 'بدون امتداد'})\n"
                f"المصدر: {result.source_path}\n"
                f"المسار: {result.path}\n"
                f"الحجم: {result.size} بايت"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, result.path)
            self.results.addItem(item)

    def show_preview(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None:
            self.preview.clear()
            return
        path = current.data(Qt.ItemDataRole.UserRole)
        preview = self.repo.get_content_preview(path)
        self.preview.setPlainText(preview or "لا توجد معاينة نصية لهذا الملف")

    def refresh_jobs_and_errors(self) -> None:
        self.jobs_list.clear()
        for job in self.repo.recent_jobs():
            self.jobs_list.addItem(
                QListWidgetItem(
                    f"Job #{job.id} | status={job.status} | indexed={job.indexed_count} | failed={job.failed_count} | started={job.started_at}"
                )
            )

        self.errors_list.clear()
        for err in self.repo.recent_errors():
            self.errors_list.addItem(
                QListWidgetItem(
                    f"[{err.created_at}] {err.stage} | {err.file_path}\n{err.message}"
                )
            )


def run_app() -> None:
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
