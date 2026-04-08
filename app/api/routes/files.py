from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app.db.session import get_db
from app.repositories.file_repository import FileRepository
from app.schemas.file import DownloadResolveResponse
from app.schemas.file import FileRead
from app.services.download_service import DownloadService

router = APIRouter(tags=["files"])


@router.get("/file/{file_id}", response_model=FileRead)
def get_file_detail(file_id: int, db=Depends(get_db)) -> FileRead:
    file_record = FileRepository(db).get_by_id(file_id)
    if file_record is None:
        raise HTTPException(status_code=404, detail="file not found")
    return FileRead.from_entity(file_record)


@router.get("/download/{file_id}")
def download_file(file_id: int, db=Depends(get_db)) -> RedirectResponse:
    service = DownloadService(db)
    try:
        result = service.resolve_download(file_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    headers = {
        "X-Download-Cache": "hit" if result.from_cache else "miss",
        "X-Download-Fallback": "1" if result.used_fallback else "0",
    }
    return RedirectResponse(url=result.target_url, status_code=302, headers=headers)


@router.post("/refresh/{file_id}", response_model=DownloadResolveResponse)
def refresh_download_cache(file_id: int, db=Depends(get_db)) -> DownloadResolveResponse:
    service = DownloadService(db)
    try:
        result = service.resolve_download(file_id, force_refresh=True)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return DownloadResolveResponse(
        file_id=result.file_id,
        target_url=result.target_url,
        from_cache=result.from_cache,
        used_fallback=result.used_fallback,
        expires_at=result.expires_at,
        error=result.error,
    )
