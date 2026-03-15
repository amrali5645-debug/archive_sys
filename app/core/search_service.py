from __future__ import annotations

from app.db.repository import Repository, SearchResult


class SearchService:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def search(self, query: str) -> list[SearchResult]:
        cleaned = query.strip()
        if not cleaned:
            return []
        return self.repository.search(cleaned)
