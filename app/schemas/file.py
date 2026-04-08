from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.entities import File


class FileRead(BaseModel):
    id: int
    source_id: int
    source_name: str
    folder_id: Optional[int]
    file_name: str
    file_path: str
    extension: Optional[str]
    size_bytes: Optional[int]
    share_url: Optional[str]
    status: str
    hot_score: int
    source_updated_at: Optional[datetime]
    direct_link_cached: bool
    direct_link_expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, file_record: File) -> "FileRead":
        cache = file_record.direct_link_cache
        return cls(
            id=file_record.id,
            source_id=file_record.source_id,
            source_name=file_record.source.name if file_record.source else "",
            folder_id=file_record.folder_id,
            file_name=file_record.file_name,
            file_path=file_record.file_path,
            extension=file_record.extension,
            size_bytes=file_record.size_bytes,
            share_url=file_record.share_url,
            status=file_record.status.value,
            hot_score=file_record.hot_score,
            source_updated_at=file_record.source_updated_at,
            direct_link_cached=bool(cache and cache.direct_url),
            direct_link_expires_at=cache.expires_at if cache else None,
            created_at=file_record.created_at,
            updated_at=file_record.updated_at,
        )


class DownloadResolveResponse(BaseModel):
    file_id: int
    target_url: str
    from_cache: bool
    used_fallback: bool
    expires_at: Optional[datetime]
    error: Optional[str] = None
