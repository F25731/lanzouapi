from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import ScanJob
from app.models.entities import SourceSource
from app.repositories.cache_repository import DirectLinkCacheRepository
from app.repositories.file_repository import FileRepository
from app.schemas.admin import MetricsResponse
from app.services.search_index_service import SearchIndexService


class MetricsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.file_repository = FileRepository(db)
        self.cache_repository = DirectLinkCacheRepository(db)
        self.search_index_service = SearchIndexService(self.file_repository)

    def collect(self) -> MetricsResponse:
        source_counts = Counter(
            status
            for status, in self.db.query(SourceSource.status).all()
        )
        scan_counts = Counter(
            status
            for status, in self.db.query(ScanJob.status).all()
        )
        search_status = self.search_index_service.get_status()

        return MetricsResponse(
            generated_at=datetime.utcnow(),
            source_status_counts={str(key.value if hasattr(key, "value") else key): int(value) for key, value in source_counts.items()},
            scan_job_status_counts={str(key.value if hasattr(key, "value") else key): int(value) for key, value in scan_counts.items()},
            file_overview=self.file_repository.stats_overview(),
            cache_overview=self.cache_repository.get_cache_overview(),
            search_backend=search_status.dict(),
        )

    def render_prometheus(self) -> str:
        metrics = self.collect()
        lines = [
            "# HELP unified_library_active_files Total active indexed files",
            "# TYPE unified_library_active_files gauge",
            "unified_library_active_files {0}".format(
                metrics.file_overview.get("active_files", 0)
            ),
            "# HELP unified_library_total_size_bytes Sum of indexed file sizes",
            "# TYPE unified_library_total_size_bytes gauge",
            "unified_library_total_size_bytes {0}".format(
                metrics.file_overview.get("total_size_bytes", 0)
            ),
            "# HELP unified_library_cache_hit_rate Direct-link cache hit rate",
            "# TYPE unified_library_cache_hit_rate gauge",
            "unified_library_cache_hit_rate {0}".format(
                metrics.cache_overview.get("hit_rate", 0)
            ),
            "# HELP unified_library_search_backend_healthy Search backend health status",
            "# TYPE unified_library_search_backend_healthy gauge",
            "unified_library_search_backend_healthy {0}".format(
                1 if metrics.search_backend.get("healthy") else 0
            ),
            "# HELP unified_library_search_backend_documents Total search index documents",
            "# TYPE unified_library_search_backend_documents gauge",
            "unified_library_search_backend_documents {0}".format(
                metrics.search_backend.get("document_count", 0)
            ),
        ]

        for status, count in sorted(metrics.source_status_counts.items()):
            lines.append(
                'unified_library_sources_total{status="%s"} %s' % (status, count)
            )

        for status, count in sorted(metrics.scan_job_status_counts.items()):
            lines.append(
                'unified_library_scan_jobs_total{status="%s"} %s' % (status, count)
            )

        return "\n".join(lines) + "\n"
