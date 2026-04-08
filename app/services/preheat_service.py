from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import List

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories.file_repository import FileRepository
from app.schemas.admin import PreheatResponse
from app.services.download_service import DownloadService


class PreheatService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.file_repository = FileRepository(db)
        self.settings = get_settings()

    def preheat(self, limit: int, min_hot_score: int) -> PreheatResponse:
        refresh_before = datetime.utcnow() + timedelta(
            seconds=self.settings.preheat_refresh_before_seconds
        )
        candidates = self.file_repository.list_preheat_candidates(
            limit=limit,
            min_hot_score=min_hot_score,
            refresh_before=refresh_before,
        )

        details: List[Dict] = []
        refreshed_count = 0
        fallback_count = 0
        failed_count = 0

        for candidate in candidates:
            force_refresh = bool(
                candidate.direct_link_cache
                and candidate.direct_link_cache.direct_url
            )
            try:
                result = DownloadService(self.db).resolve_download(
                    candidate.id,
                    force_refresh=force_refresh,
                )
                refreshed_count += 1
                if result.used_fallback:
                    fallback_count += 1
                details.append(
                    {
                        "file_id": candidate.id,
                        "file_name": candidate.file_name,
                        "status": "fallback" if result.used_fallback else "refreshed",
                    }
                )
            except Exception as exc:
                self.db.rollback()
                failed_count += 1
                details.append(
                    {
                        "file_id": candidate.id,
                        "file_name": candidate.file_name,
                        "status": "failed",
                        "error": str(exc),
                    }
                )

        return PreheatResponse(
            scanned_candidates=len(candidates),
            refreshed_count=refreshed_count,
            fallback_count=fallback_count,
            failed_count=failed_count,
            details=details,
        )
