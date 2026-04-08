from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import DirectLinkCache


class DirectLinkCacheRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_file_id(self, file_id: int) -> Optional[DirectLinkCache]:
        return (
            self.db.query(DirectLinkCache)
            .filter(DirectLinkCache.file_id == file_id)
            .first()
        )

    def mark_hit(self, file_id: int) -> None:
        cache = self.get_by_file_id(file_id)
        if cache is None:
            cache = DirectLinkCache(
                file_id=file_id,
                hit_count=0,
                miss_count=0,
                fail_count=0,
            )
        cache.hit_count = cache.hit_count or 0
        cache.hit_count += 1
        self.db.add(cache)
        self.db.flush()

    def mark_miss(self, file_id: int) -> None:
        cache = self.get_by_file_id(file_id)
        if cache is None:
            cache = DirectLinkCache(
                file_id=file_id,
                hit_count=0,
                miss_count=0,
                fail_count=0,
            )
        cache.miss_count = cache.miss_count or 0
        cache.miss_count += 1
        self.db.add(cache)
        self.db.flush()

    def upsert_success(
        self,
        file_id: int,
        direct_url: str,
        expires_at: Optional[datetime],
    ) -> DirectLinkCache:
        cache = self.get_by_file_id(file_id)
        if cache is None:
            cache = DirectLinkCache(
                file_id=file_id,
                hit_count=0,
                miss_count=0,
                fail_count=0,
            )
        cache.direct_url = direct_url
        cache.resolved_at = datetime.utcnow()
        cache.expires_at = expires_at
        cache.fail_count = 0
        cache.last_error = None
        cache.next_retry_at = None
        self.db.add(cache)
        self.db.flush()
        return cache

    def record_failure(
        self,
        file_id: int,
        error_message: str,
        retry_after_seconds: int,
    ) -> DirectLinkCache:
        cache = self.get_by_file_id(file_id)
        if cache is None:
            cache = DirectLinkCache(
                file_id=file_id,
                hit_count=0,
                miss_count=0,
                fail_count=0,
            )
        cache.fail_count = cache.fail_count or 0
        cache.fail_count += 1
        cache.last_error = error_message
        cache.next_retry_at = datetime.utcnow() + timedelta(seconds=retry_after_seconds)
        self.db.add(cache)
        self.db.flush()
        return cache

    def invalidate(self, file_id: int) -> None:
        cache = self.get_by_file_id(file_id)
        if cache is None:
            return
        cache.direct_url = None
        cache.expires_at = None
        cache.resolved_at = None
        self.db.add(cache)
        self.db.flush()

    def get_cache_overview(self) -> dict:
        now = datetime.utcnow()
        total_entries = self.db.query(func.count(DirectLinkCache.id)).scalar() or 0
        valid_entries = (
            self.db.query(func.count(DirectLinkCache.id))
            .filter(DirectLinkCache.direct_url.isnot(None))
            .filter(
                (DirectLinkCache.expires_at.is_(None))
                | (DirectLinkCache.expires_at > now)
            )
            .scalar()
            or 0
        )
        total_hits = self.db.query(func.coalesce(func.sum(DirectLinkCache.hit_count), 0)).scalar() or 0
        total_misses = self.db.query(func.coalesce(func.sum(DirectLinkCache.miss_count), 0)).scalar() or 0
        hit_rate = 0.0
        if total_hits + total_misses > 0:
            hit_rate = float(total_hits) / float(total_hits + total_misses)

        return {
            "total_entries": int(total_entries),
            "valid_entries": int(valid_entries),
            "total_hits": int(total_hits),
            "total_misses": int(total_misses),
            "hit_rate": round(hit_rate, 4),
        }
