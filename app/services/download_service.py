from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.providers.registry import provider_registry
from app.repositories.cache_repository import DirectLinkCacheRepository
from app.repositories.file_repository import FileRepository
from app.utils.locks import resolve_lock_manager


@dataclass
class DownloadResolution:
    file_id: int
    target_url: str
    from_cache: bool
    used_fallback: bool
    expires_at: Optional[datetime]
    error: Optional[str] = None


class DownloadService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.file_repository = FileRepository(db)
        self.cache_repository = DirectLinkCacheRepository(db)
        self.settings = get_settings()

    def get_file_or_raise(self, file_id: int):
        file_record = self.file_repository.get_by_id(file_id)
        if file_record is None:
            raise LookupError("file not found")
        return file_record

    def resolve_download(
        self,
        file_id: int,
        force_refresh: bool = False,
    ) -> DownloadResolution:
        file_record = self.get_file_or_raise(file_id)
        if force_refresh:
            self.cache_repository.invalidate(file_id)
            self.db.flush()
            file_record = self.file_repository.get_by_id(file_id)

        cached_target = self._get_valid_cached_url(file_record)
        if cached_target:
            self.cache_repository.mark_hit(file_id)
            self.file_repository.increment_download_count(file_id)
            self.db.commit()
            return DownloadResolution(
                file_id=file_id,
                target_url=cached_target,
                from_cache=True,
                used_fallback=False,
                expires_at=file_record.direct_link_cache.expires_at,
            )

        self.cache_repository.mark_miss(file_id)
        lock_key = f"resolve:file:{file_id}"
        lock_handle = resolve_lock_manager.acquire(
            lock_key,
            self.settings.direct_link_lock_timeout_seconds,
        )

        if lock_handle is None:
            return self._wait_or_fallback(file_id)

        try:
            self.db.expire_all()
            file_record = self.get_file_or_raise(file_id)
            cached_target = self._get_valid_cached_url(file_record)
            if cached_target:
                self.cache_repository.mark_hit(file_id)
                self.file_repository.increment_download_count(file_id)
                self.db.commit()
                return DownloadResolution(
                    file_id=file_id,
                    target_url=cached_target,
                    from_cache=True,
                    used_fallback=False,
                    expires_at=file_record.direct_link_cache.expires_at,
                )

            if self._is_in_backoff(file_record):
                self.db.commit()
                return self._fallback_or_raise(file_record, "resolver in backoff window")

            provider = provider_registry.get(file_record.source.adapter_type)
            result = provider.resolve_direct_link(file_record.source, file_record)
            expires_at = result.expires_at or (
                datetime.utcnow()
                + timedelta(seconds=self.settings.direct_link_ttl_seconds)
            )
            self.cache_repository.upsert_success(file_id, result.direct_url, expires_at)
            self.file_repository.increment_download_count(file_id)
            self.db.commit()
            return DownloadResolution(
                file_id=file_id,
                target_url=result.direct_url,
                from_cache=False,
                used_fallback=False,
                expires_at=expires_at,
            )
        except Exception as exc:
            self.db.rollback()
            existing_cache = self.cache_repository.get_by_file_id(file_id)
            existing_fail_count = existing_cache.fail_count if existing_cache else 0
            retry_after_seconds = self.settings.direct_link_retry_base_seconds * (
                2 ** min(existing_fail_count, 5)
            )
            self.cache_repository.record_failure(
                file_id=file_id,
                error_message=str(exc),
                retry_after_seconds=retry_after_seconds,
            )
            self.db.commit()
            return self._fallback_or_raise(file_record, str(exc))
        finally:
            lock_handle.release()

    def _wait_or_fallback(self, file_id: int) -> DownloadResolution:
        deadline = datetime.utcnow() + timedelta(
            seconds=self.settings.direct_link_wait_seconds
        )
        while datetime.utcnow() < deadline:
            resolve_lock_manager.sleep(0.5)
            self.db.expire_all()
            file_record = self.get_file_or_raise(file_id)
            cached_target = self._get_valid_cached_url(file_record)
            if cached_target:
                self.cache_repository.mark_hit(file_id)
                self.file_repository.increment_download_count(file_id)
                self.db.commit()
                return DownloadResolution(
                    file_id=file_id,
                    target_url=cached_target,
                    from_cache=True,
                    used_fallback=False,
                    expires_at=file_record.direct_link_cache.expires_at,
                )

        file_record = self.get_file_or_raise(file_id)
        self.db.commit()
        return self._fallback_or_raise(file_record, "resolver busy")

    def _get_valid_cached_url(self, file_record) -> Optional[str]:
        cache = file_record.direct_link_cache
        if not cache or not cache.direct_url:
            return None
        if cache.expires_at and cache.expires_at <= datetime.utcnow():
            return None
        return cache.direct_url

    def _is_in_backoff(self, file_record) -> bool:
        cache = file_record.direct_link_cache
        if not cache or not cache.next_retry_at:
            return False
        return cache.next_retry_at > datetime.utcnow()

    def _fallback_or_raise(self, file_record, error_message: str) -> DownloadResolution:
        if file_record.share_url:
            return DownloadResolution(
                file_id=file_record.id,
                target_url=file_record.share_url,
                from_cache=False,
                used_fallback=True,
                expires_at=None,
                error=error_message,
            )
        raise RuntimeError(error_message)
