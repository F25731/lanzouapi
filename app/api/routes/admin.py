from __future__ import annotations

from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.enums import ScanMode
from app.models.enums import SourceStatus
from app.core.errors import AppError
from app.repositories.cache_repository import DirectLinkCacheRepository
from app.repositories.file_repository import FileRepository
from app.repositories.source_repository import SourceRepository
from app.schemas.admin import ApiClientCreateRequest
from app.schemas.admin import ApiClientRead
from app.schemas.admin import ApiClientSecretResponse
from app.schemas.admin import CacheOverviewResponse
from app.schemas.admin import HotFileRead
from app.schemas.admin import MetricsResponse
from app.schemas.admin import PreheatRequest
from app.schemas.admin import PreheatResponse
from app.schemas.admin import ReindexRequest
from app.schemas.admin import ReindexResponse
from app.schemas.admin import RescanRequest
from app.schemas.admin import ScanJobRead
from app.schemas.admin import SearchBackendStatusResponse
from app.schemas.admin import SourceLoginTestResponse
from app.schemas.admin import SourceStatusItem
from app.schemas.source import SourceCreate
from app.schemas.source import SourceRead
from app.schemas.source import SourceUpdate
from app.services.auth_service import AuthService
from app.services.metrics_service import MetricsService
from app.services.preheat_service import PreheatService
from app.services.scan_service import ScanService
from app.services.search_index_service import SearchIndexService
from app.services.source_service import SourceService

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


BASIC_API_SCOPES = ["search:read", "file:read", "download:read"]


@router.get("/sources", response_model=List[SourceRead])
def list_sources(db=Depends(get_db)) -> List[SourceRead]:
    service = SourceService(SourceRepository(db))
    return [SourceRead.from_entity(item) for item in service.list_sources()]


@router.post("/sources", response_model=SourceRead)
def create_source(payload: SourceCreate, db=Depends(get_db)) -> SourceRead:
    service = SourceService(SourceRepository(db))
    try:
        source = service.create_source(payload)
        db.commit()
        return SourceRead.from_entity(source)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/source/{source_id}", response_model=SourceRead)
def update_source(source_id: int, payload: SourceUpdate, db=Depends(get_db)) -> SourceRead:
    service = SourceService(SourceRepository(db))
    try:
        source = service.update_source(source_id, payload)
        db.commit()
        return SourceRead.from_entity(source)
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/source/{source_id}/disable", response_model=SourceRead)
def disable_source(source_id: int, db=Depends(get_db)) -> SourceRead:
    service = SourceService(SourceRepository(db))
    try:
        source = service.disable_source(source_id)
        db.commit()
        return SourceRead.from_entity(source)
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/source/{source_id}/login-test", response_model=SourceLoginTestResponse)
def test_source_login(source_id: int, db=Depends(get_db)) -> SourceLoginTestResponse:
    service = SourceService(SourceRepository(db))
    try:
        source = service.test_login(source_id)
        db.commit()
        return SourceLoginTestResponse.from_entity(source, success=True)
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        source = service.source_repository.get_source(source_id)
        if source is None:
            raise HTTPException(status_code=404, detail="source not found") from exc
        source.last_error = str(exc)
        source.status = SourceStatus.ERROR
        db.add(source)
        db.commit()
        db.refresh(source)
        return SourceLoginTestResponse.from_entity(source, success=False)


@router.get("/source-status", response_model=List[SourceStatusItem])
def get_source_status(db=Depends(get_db)) -> List[SourceStatusItem]:
    repository = SourceRepository(db)
    return [SourceStatusItem.from_entity(item) for item in repository.list_sources()]


@router.get("/scan-jobs", response_model=List[ScanJobRead])
def get_scan_jobs(db=Depends(get_db)) -> List[ScanJobRead]:
    service = ScanService(db)
    return [ScanJobRead.from_entity(job) for job in service.list_recent_jobs()]


@router.post("/source/{source_id}/rescan", response_model=ScanJobRead)
def rescan_source(source_id: int, payload: RescanRequest, db=Depends(get_db)) -> ScanJobRead:
    service = ScanService(db)
    try:
        mode = ScanMode(payload.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid scan mode") from exc

    try:
        job = service.enqueue_scan(
            source_id=source_id,
            provider_folder_id=payload.provider_folder_id,
            mode=mode,
            requested_by="admin_api",
        )
        return ScanJobRead.from_entity(job)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cache-overview", response_model=CacheOverviewResponse)
def cache_overview(db=Depends(get_db)) -> CacheOverviewResponse:
    repository = DirectLinkCacheRepository(db)
    return CacheOverviewResponse(**repository.get_cache_overview())


@router.get("/hot-files", response_model=List[HotFileRead])
def hot_files(db=Depends(get_db)) -> List[HotFileRead]:
    repository = FileRepository(db)
    return [HotFileRead.from_entity(item) for item in repository.list_hot_files()]


@router.get("/search-backend", response_model=SearchBackendStatusResponse)
def search_backend_status(db=Depends(get_db)) -> SearchBackendStatusResponse:
    service = SearchIndexService(FileRepository(db))
    return service.get_status()


@router.post("/reindex", response_model=ReindexResponse)
def reindex(payload: ReindexRequest, db=Depends(get_db)) -> ReindexResponse:
    service = SearchIndexService(FileRepository(db))
    return service.reindex_all(
        source_id=payload.source_id,
        batch_size=payload.batch_size,
    )


@router.post("/preheat", response_model=PreheatResponse)
def preheat(payload: PreheatRequest, db=Depends(get_db)) -> PreheatResponse:
    service = PreheatService(db)
    return service.preheat(limit=payload.limit, min_hot_score=payload.min_hot_score)


@router.get("/metrics", response_model=MetricsResponse)
def metrics(db=Depends(get_db)) -> MetricsResponse:
    return MetricsService(db).collect()


@router.post("/api-client/create", response_model=ApiClientSecretResponse)
def create_api_client(payload: ApiClientCreateRequest, db=Depends(get_db)) -> ApiClientSecretResponse:
    service = AuthService(db)
    scopes = payload.scopes or BASIC_API_SCOPES
    try:
        client, api_key = service.create_api_client(
            client_name=payload.client_name,
            client_type=payload.client_type,
            scopes=scopes,
            rate_limit_per_min=payload.rate_limit_per_min,
            ip_whitelist=payload.ip_whitelist or [],
        )
        db.commit()
        return ApiClientSecretResponse(
            client=ApiClientRead.from_entity(client),
            api_key=api_key,
        )
    except AppError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/api-clients", response_model=List[ApiClientRead])
def list_api_clients(db=Depends(get_db)) -> List[ApiClientRead]:
    service = AuthService(db)
    return [ApiClientRead.from_entity(item) for item in service.list_api_clients()]


@router.post("/api-client/{client_id}/disable", response_model=ApiClientRead)
def disable_api_client(client_id: int, db=Depends(get_db)) -> ApiClientRead:
    service = AuthService(db)
    try:
        client = service.set_api_client_status(client_id, enabled=False)
        db.commit()
        return ApiClientRead.from_entity(client)
    except AppError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/api-client/{client_id}/enable", response_model=ApiClientRead)
def enable_api_client(client_id: int, db=Depends(get_db)) -> ApiClientRead:
    service = AuthService(db)
    try:
        client = service.set_api_client_status(client_id, enabled=True)
        db.commit()
        return ApiClientRead.from_entity(client)
    except AppError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/api-client/{client_id}/rotate", response_model=ApiClientSecretResponse)
def rotate_api_client(client_id: int, db=Depends(get_db)) -> ApiClientSecretResponse:
    service = AuthService(db)
    try:
        client, api_key = service.rotate_api_client_key(client_id)
        db.commit()
        return ApiClientSecretResponse(
            client=ApiClientRead.from_entity(client),
            api_key=api_key,
        )
    except AppError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
