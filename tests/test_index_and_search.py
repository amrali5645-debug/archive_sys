from pathlib import Path

from app.core.indexer import Indexer
from app.core.search_service import SearchService
from app.db.database import ensure_db
from app.db.repository import Repository


def test_index_and_search_with_filters_and_jobs(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "hello.txt").write_text("this is archive searchable content", encoding="utf-8")
    (source / "data.json").write_text('{"k":"searchable json"}', encoding="utf-8")

    conn = ensure_db(tmp_path / "data" / "test.db")
    repo = Repository(conn)

    progress_calls: list[tuple[int, int, str]] = []

    stats = Indexer(repo).index_source(
        source,
        progress_callback=lambda c, t, p: progress_calls.append((c, t, p)),
    )
    assert stats["indexed"] == 2
    assert stats["job_id"] > 0
    assert len(progress_calls) == 2

    jobs = repo.recent_jobs(limit=1)
    assert jobs[0].indexed_count == 2
    assert jobs[0].failed_count == 0

    service = SearchService(repo)

    all_results = service.search("searchable")
    assert len(all_results) == 2

    txt_results = service.search("searchable", ext_filter=".txt")
    assert len(txt_results) == 1
    assert txt_results[0].filename == "hello.txt"

    source_results = service.search("searchable", source_filter=str(source.resolve()))
    assert len(source_results) == 2

    preview = repo.get_content_preview(str((source / "hello.txt").resolve()))
    assert "searchable" in preview

    stats_view = repo.get_dashboard_stats()
    assert stats_view.total_sources == 1
    assert stats_view.total_files == 2
    assert stats_view.total_jobs >= 1


def test_indexer_stop_marks_job_stopped(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    for i in range(5):
        (source / f"f{i}.txt").write_text(f"file {i}", encoding="utf-8")

    conn = ensure_db(tmp_path / "data" / "test.db")
    repo = Repository(conn)

    first = True

    def should_stop() -> bool:
        nonlocal first
        if first:
            first = False
            return False
        return True

    stats = Indexer(repo).index_source(source, should_stop=should_stop)
    assert stats["indexed"] == 1

    latest_job = repo.recent_jobs(limit=1)[0]
    assert latest_job.status == "stopped"
