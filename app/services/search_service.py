from __future__ import annotations

from typing import Dict

from sqlalchemy.orm import Session

from app.schemas.file import FileRead
from app.schemas.search import SearchRequest
from app.schemas.search import SearchResponse
from app.services.search_index_service import SearchIndexService


class SearchService:
    def __init__(self, db: Session) -> None:
        from app.repositories.file_repository import FileRepository

        self.file_repository = FileRepository(db)
        self.search_index_service = SearchIndexService(self.file_repository)

    def search(self, payload: SearchRequest) -> SearchResponse:
        total = 0
        items = []
        backend = "database"

        engine_result = self.search_index_service.search(payload)
        if engine_result is not None and engine_result.file_ids:
            total = engine_result.total
            items = self._ordered_files(engine_result.file_ids)
            backend = engine_result.backend
        elif engine_result is not None:
            total = engine_result.total
            items = []
            backend = engine_result.backend
        else:
            total, items = self.file_repository.search(
                keyword=payload.keyword,
                source_ids=payload.source_ids,
                extensions=payload.extensions,
                min_size=payload.min_size,
                max_size=payload.max_size,
                sort_by=payload.sort_by,
                sort_order=payload.sort_order,
                page=payload.page,
                size=payload.size,
            )

        self.file_repository.increment_search_counts([item.id for item in items])
        return SearchResponse(
            total=total,
            page=payload.page,
            size=payload.size,
            backend=backend,
            items=[FileRead.from_entity(item) for item in items],
        )

    def _ordered_files(self, file_ids):
        by_id: Dict[int, object] = {
            item.id: item for item in self.file_repository.get_by_ids(file_ids)
        }
        return [by_id[file_id] for file_id in file_ids if file_id in by_id]
