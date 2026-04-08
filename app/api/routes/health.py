from __future__ import annotations

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_engine
from app.services.search_index_service import SearchIndexService

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    settings = get_settings()
    db_status = "ok"
    redis_status = "disabled"
    search_status = "disabled"

    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    if settings.redis_url and redis is not None:
        try:
            redis.from_url(settings.redis_url).ping()
            redis_status = "ok"
        except Exception:
            redis_status = "error"

    search_backend = SearchIndexService().get_status()
    if search_backend.enabled:
        search_status = "ok" if search_backend.healthy else "error"

    return {
        "status": "ok"
        if db_status == "ok" and search_status in {"ok", "disabled"}
        else "degraded",
        "database": db_status,
        "redis": redis_status,
        "search": search_status,
    }
