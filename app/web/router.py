from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi.responses import HTMLResponse
from fastapi.responses import PlainTextResponse

from app.api.deps import require_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.services.metrics_service import MetricsService
from app.web.panel_template import render_admin_panel_html

web_router = APIRouter()


@web_router.get("/metrics", response_class=PlainTextResponse)
def metrics_export(db=Depends(get_db)) -> str:
    return MetricsService(db).render_prometheus()


@web_router.get(
    "/admin/panel",
    response_class=HTMLResponse,
    dependencies=[Depends(require_admin)],
)
def admin_panel(token: Optional[str] = Query(default=None)) -> HTMLResponse:
    settings = get_settings()
    return HTMLResponse(
        content=render_admin_panel_html(
            api_prefix=settings.api_prefix,
            token=token or "",
        )
    )
