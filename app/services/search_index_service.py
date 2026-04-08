from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional

import httpx

from app.core.config import get_settings
from app.models.entities import File
from app.repositories.file_repository import FileRepository
from app.schemas.admin import ReindexResponse
from app.schemas.admin import SearchBackendStatusResponse
from app.schemas.search import SearchRequest
from app.utils.files import normalize_name


logger = logging.getLogger(__name__)


@dataclass
class SearchExecutionResult:
    total: int
    file_ids: List[int]
    backend: str


class SearchIndexService:
    def __init__(self, file_repository: Optional[FileRepository] = None) -> None:
        self.settings = get_settings()
        self.file_repository = file_repository

    def is_enabled(self) -> bool:
        return bool(self.settings.opensearch_url)

    def search(self, payload: SearchRequest) -> Optional[SearchExecutionResult]:
        if not self.is_enabled():
            return None

        try:
            response = self._request("GET", "/")
            if response.status_code >= 400:
                return None

            search_response = self._request(
                "POST",
                f"/{self.settings.opensearch_index_name}/_search",
                json=self._build_search_body(payload),
            )
            if search_response.status_code == 404:
                return None
            search_response.raise_for_status()

            body = search_response.json()
            hits = body.get("hits", {})
            total = hits.get("total", {})
            total_value = total.get("value", 0) if isinstance(total, dict) else int(total or 0)
            file_ids = [
                int(hit.get("_source", {}).get("file_id"))
                for hit in hits.get("hits", [])
                if hit.get("_source", {}).get("file_id") is not None
            ]
            return SearchExecutionResult(
                total=int(total_value),
                file_ids=file_ids,
                backend="opensearch",
            )
        except Exception:
            logger.exception("opensearch search failed, falling back to database")
            return None

    def sync_files_by_ids(self, file_ids: List[int]) -> int:
        if not self.is_enabled() or not self.file_repository or not file_ids:
            return 0

        unique_ids = sorted(set(file_ids))
        self.ensure_index()
        synced = 0

        for start in range(0, len(unique_ids), self.settings.search_sync_batch_size):
            batch_ids = unique_ids[start : start + self.settings.search_sync_batch_size]
            files = self.file_repository.get_by_ids(batch_ids)
            if not files:
                continue

            lines = []
            for file_record in files:
                lines.append(
                    self._ndjson(
                        {
                            "index": {
                                "_index": self.settings.opensearch_index_name,
                                "_id": str(file_record.id),
                            }
                        }
                    )
                )
                lines.append(self._ndjson(self._build_document(file_record)))

            payload = "\n".join(lines) + "\n"
            response = self._request(
                "POST",
                "/_bulk",
                content=payload,
                headers={"Content-Type": "application/x-ndjson"},
            )
            response.raise_for_status()
            body = response.json()
            if body.get("errors"):
                raise RuntimeError("opensearch bulk sync returned errors")
            synced += len(files)

        return synced

    def delete_files_by_ids(self, file_ids: List[int]) -> int:
        if not self.is_enabled() or not file_ids:
            return 0

        unique_ids = sorted(set(file_ids))
        lines = [
            self._ndjson(
                {
                    "delete": {
                        "_index": self.settings.opensearch_index_name,
                        "_id": str(file_id),
                    }
                }
            )
            for file_id in unique_ids
        ]
        response = self._request(
            "POST",
            "/_bulk",
            content="\n".join(lines) + "\n",
            headers={"Content-Type": "application/x-ndjson"},
        )
        if response.status_code == 404:
            return 0
        response.raise_for_status()
        return len(unique_ids)

    def reindex_all(self, source_id: Optional[int], batch_size: int) -> ReindexResponse:
        if not self.file_repository:
            raise ValueError("file_repository is required for reindexing")
        if not self.is_enabled():
            return ReindexResponse(
                indexed_count=0,
                deleted_count=0,
                batches=0,
                backend="database",
                source_id=source_id,
                last_id=0,
            )

        self.ensure_index()
        indexed_count = 0
        batches = 0
        last_id = 0

        while True:
            batch = self.file_repository.list_active_batch(
                limit=batch_size,
                last_id=last_id,
                source_id=source_id,
            )
            if not batch:
                break

            self.sync_files_by_ids([item.id for item in batch])
            indexed_count += len(batch)
            batches += 1
            last_id = batch[-1].id

        return ReindexResponse(
            indexed_count=indexed_count,
            deleted_count=0,
            batches=batches,
            backend="opensearch",
            source_id=source_id,
            last_id=last_id,
        )

    def ensure_index(self) -> None:
        if not self.is_enabled():
            return

        head_response = self._request(
            "HEAD",
            f"/{self.settings.opensearch_index_name}",
        )
        if head_response.status_code == 200:
            return
        if head_response.status_code not in {404, 400}:
            head_response.raise_for_status()

        response = self._request(
            "PUT",
            f"/{self.settings.opensearch_index_name}",
            json={
                "settings": {
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                    }
                },
                "mappings": {
                    "properties": {
                        "file_id": {"type": "integer"},
                        "source_id": {"type": "integer"},
                        "source_name": {"type": "keyword"},
                        "folder_id": {"type": "integer"},
                        "file_name": {
                            "type": "text",
                            "fields": {
                                "keyword": {"type": "keyword", "ignore_above": 256}
                            },
                        },
                        "normalized_name": {"type": "text"},
                        "file_path": {
                            "type": "text",
                            "fields": {
                                "keyword": {"type": "keyword", "ignore_above": 1024}
                            },
                        },
                        "extension": {"type": "keyword"},
                        "size_bytes": {"type": "long"},
                        "share_url": {"type": "keyword", "index": False},
                        "hot_score": {"type": "integer"},
                        "updated_at": {"type": "date"},
                        "source_updated_at": {"type": "date"},
                    }
                },
            },
        )
        if response.status_code not in {200, 201}:
            response.raise_for_status()

    def get_status(self) -> SearchBackendStatusResponse:
        if not self.is_enabled():
            return SearchBackendStatusResponse(
                enabled=False,
                healthy=False,
                backend="database",
                index_name=self.settings.opensearch_index_name,
                document_count=0,
                last_error=None,
            )

        try:
            root_response = self._request("GET", "/")
            root_response.raise_for_status()

            count_response = self._request(
                "GET",
                f"/{self.settings.opensearch_index_name}/_count",
            )
            if count_response.status_code == 404:
                return SearchBackendStatusResponse(
                    enabled=True,
                    healthy=True,
                    backend="opensearch",
                    index_name=self.settings.opensearch_index_name,
                    document_count=0,
                    last_error=None,
                )
            count_response.raise_for_status()
            body = count_response.json()
            return SearchBackendStatusResponse(
                enabled=True,
                healthy=True,
                backend="opensearch",
                index_name=self.settings.opensearch_index_name,
                document_count=int(body.get("count", 0)),
                last_error=None,
            )
        except Exception as exc:
            return SearchBackendStatusResponse(
                enabled=True,
                healthy=False,
                backend="opensearch",
                index_name=self.settings.opensearch_index_name,
                document_count=0,
                last_error=str(exc),
            )

    def _build_search_body(self, payload: SearchRequest) -> Dict:
        filters = []
        if payload.source_ids:
            filters.append({"terms": {"source_id": payload.source_ids}})
        if payload.extensions:
            filters.append(
                {"terms": {"extension": [item.lower() for item in payload.extensions]}}
            )
        if payload.min_size is not None or payload.max_size is not None:
            size_range = {}
            if payload.min_size is not None:
                size_range["gte"] = payload.min_size
            if payload.max_size is not None:
                size_range["lte"] = payload.max_size
            filters.append({"range": {"size_bytes": size_range}})

        must = []
        if payload.keyword:
            normalized = normalize_name(payload.keyword)
            must.append(
                {
                    "bool": {
                        "should": [
                            {
                                "multi_match": {
                                    "query": payload.keyword,
                                    "type": "bool_prefix",
                                    "fields": [
                                        "file_name^3",
                                        "file_path^2",
                                        "extension",
                                    ],
                                }
                            },
                            {
                                "match": {
                                    "file_name": {
                                        "query": payload.keyword,
                                        "fuzziness": "AUTO",
                                        "boost": 2,
                                    }
                                }
                            },
                            {
                                "match_phrase_prefix": {
                                    "file_name": {
                                        "query": payload.keyword,
                                        "boost": 3,
                                    }
                                }
                            },
                            {
                                "match": {
                                    "normalized_name": {
                                        "query": normalized,
                                        "operator": "and",
                                        "boost": 2,
                                    }
                                }
                            },
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )

        sort_field = {
            "size_bytes": "size_bytes",
            "hot_score": "hot_score",
            "file_name": "file_name.keyword",
            "updated_at": "updated_at",
        }.get(payload.sort_by, "updated_at")
        sort_order = payload.sort_order if payload.sort_order in {"asc", "desc"} else "desc"

        return {
            "from": (payload.page - 1) * payload.size,
            "size": payload.size,
            "_source": [
                "file_id",
                "file_name",
                "source_id",
                "source_name",
                "extension",
                "size_bytes",
                "updated_at",
            ],
            "query": {
                "bool": {
                    "must": must or [{"match_all": {}}],
                    "filter": filters,
                }
            },
            "sort": [{sort_field: {"order": sort_order}}],
        }

    def _build_document(self, file_record: File) -> Dict:
        return {
            "file_id": file_record.id,
            "source_id": file_record.source_id,
            "source_name": file_record.source.name if file_record.source else "",
            "folder_id": file_record.folder_id,
            "file_name": file_record.file_name,
            "normalized_name": file_record.normalized_name,
            "file_path": file_record.file_path,
            "extension": file_record.extension,
            "size_bytes": file_record.size_bytes,
            "share_url": file_record.share_url,
            "hot_score": file_record.hot_score,
            "updated_at": file_record.updated_at.isoformat()
            if file_record.updated_at
            else datetime.utcnow().isoformat(),
            "source_updated_at": file_record.source_updated_at.isoformat()
            if file_record.source_updated_at
            else None,
        }

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        base_url = self.settings.opensearch_url.rstrip("/")
        with httpx.Client(base_url=base_url, timeout=self.settings.opensearch_timeout_seconds) as client:
            return client.request(method, path, **kwargs)

    def _ndjson(self, data: Dict) -> str:
        import json

        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
