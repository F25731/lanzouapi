from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from app.models.entities import File
from app.models.entities import ScanJob
from app.models.entities import SourceSource
from app.models.entities import ApiClient
from app.utils.serialization import loads_json
from app.utils.scopes import parse_ip_whitelist
from app.utils.scopes import parse_scopes


class SourceStatusItem(BaseModel):
    id: int
    name: str
    adapter_type: str
    status: str
    is_enabled: bool
    last_sync_at: Optional[datetime]
    last_error: Optional[str]
    rate_limit_per_minute: int

    @classmethod
    def from_entity(cls, source: SourceSource) -> "SourceStatusItem":
        return cls(
            id=source.id,
            name=source.name,
            adapter_type=source.adapter_type,
            status=source.status.value,
            is_enabled=source.is_enabled,
            last_sync_at=source.last_sync_at,
            last_error=source.last_error,
            rate_limit_per_minute=source.rate_limit_per_minute,
        )


class ScanJobRead(BaseModel):
    id: int
    source_id: int
    mode: str
    status: str
    target_provider_folder_id: Optional[str]
    progress_current: int
    progress_total: Optional[int]
    error_message: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    summary: Dict
    created_at: datetime

    @classmethod
    def from_entity(cls, job: ScanJob) -> "ScanJobRead":
        return cls(
            id=job.id,
            source_id=job.source_id,
            mode=job.mode.value,
            status=job.status.value,
            target_provider_folder_id=job.target_provider_folder_id,
            progress_current=job.progress_current,
            progress_total=job.progress_total,
            error_message=job.error_message,
            started_at=job.started_at,
            finished_at=job.finished_at,
            summary=loads_json(job.summary_json, {}),
            created_at=job.created_at,
        )


class CacheOverviewResponse(BaseModel):
    total_entries: int
    valid_entries: int
    total_hits: int
    total_misses: int
    hit_rate: float


class HotFileRead(BaseModel):
    id: int
    file_name: str
    source_name: str
    hot_score: int
    download_count: int
    search_count: int

    @classmethod
    def from_entity(cls, file_record: File) -> "HotFileRead":
        return cls(
            id=file_record.id,
            file_name=file_record.file_name,
            source_name=file_record.source.name if file_record.source else "",
            hot_score=file_record.hot_score,
            download_count=file_record.stats.download_count if file_record.stats else 0,
            search_count=file_record.stats.search_count if file_record.stats else 0,
        )


class RescanRequest(BaseModel):
    provider_folder_id: Optional[str] = Field(default=None, max_length=120)
    mode: str = Field(default="rescan")


class SearchBackendStatusResponse(BaseModel):
    enabled: bool
    healthy: bool
    backend: str
    index_name: str
    document_count: int
    last_error: Optional[str] = None


class ReindexRequest(BaseModel):
    source_id: Optional[int] = None
    batch_size: int = Field(default=500, ge=1, le=5000)


class ReindexResponse(BaseModel):
    indexed_count: int
    deleted_count: int = 0
    batches: int
    backend: str
    source_id: Optional[int] = None
    last_id: int = 0


class PreheatRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)
    min_hot_score: int = Field(default=1, ge=0)


class PreheatResponse(BaseModel):
    scanned_candidates: int
    refreshed_count: int
    fallback_count: int
    failed_count: int
    details: List[Dict[str, Any]]


class MetricsResponse(BaseModel):
    generated_at: datetime
    source_status_counts: Dict[str, int]
    scan_job_status_counts: Dict[str, int]
    file_overview: Dict[str, int]
    cache_overview: Dict[str, Any]
    search_backend: Dict[str, Any]


class SourceLoginTestResponse(BaseModel):
    id: int
    name: str
    adapter_type: str
    success: bool
    status: str
    last_login_at: Optional[datetime]
    last_error: Optional[str]

    @classmethod
    def from_entity(
        cls,
        source: SourceSource,
        *,
        success: bool,
    ) -> "SourceLoginTestResponse":
        return cls(
            id=source.id,
            name=source.name,
            adapter_type=source.adapter_type,
            success=success,
            status=source.status.value,
            last_login_at=source.last_login_at,
            last_error=source.last_error,
        )


class ApiClientCreateRequest(BaseModel):
    client_name: str = Field(..., min_length=1, max_length=120)
    client_type: str = Field(default="robot", min_length=1, max_length=50)
    scopes: Optional[List[str]] = None
    rate_limit_per_min: int = Field(default=60, ge=1, le=100000)
    ip_whitelist: Optional[List[str]] = None


class ApiClientRead(BaseModel):
    id: int
    client_name: str
    client_type: str
    key_prefix: str
    status: str
    scopes: List[str]
    rate_limit_per_min: int
    ip_whitelist: List[str]
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, client: ApiClient) -> "ApiClientRead":
        return cls(
            id=client.id,
            client_name=client.client_name,
            client_type=client.client_type,
            key_prefix=client.key_prefix,
            status=client.status.value,
            scopes=parse_scopes(client.scopes),
            rate_limit_per_min=client.rate_limit_per_min,
            ip_whitelist=parse_ip_whitelist(client.ip_whitelist),
            last_used_at=client.last_used_at,
            created_at=client.created_at,
            updated_at=client.updated_at,
        )


class ApiClientSecretResponse(BaseModel):
    client: ApiClientRead
    api_key: str
