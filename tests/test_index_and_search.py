from pathlib import Path

from app.core.indexer import Indexer
from app.core.search_service import SearchService
from app.db.database import ensure_db
from app.db.repository import Repository


def test_index_and_search(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "hello.txt").write_text("this is archive searchable content", encoding="utf-8")

    conn = ensure_db(tmp_path / "data" / "test.db")
    repo = Repository(conn)

    stats = Indexer(repo).index_source(source)
    assert stats["indexed"] == 1

    results = SearchService(repo).search("searchable")
    assert len(results) == 1
    assert results[0].filename == "hello.txt"
