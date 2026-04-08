from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends

from app.db.session import get_db
from app.schemas.search import SearchRequest
from app.schemas.search import SearchResponse
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search_files(payload: SearchRequest, db=Depends(get_db)) -> SearchResponse:
    service = SearchService(db)
    response = service.search(payload)
    db.commit()
    return response
