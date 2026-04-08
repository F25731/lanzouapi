from __future__ import annotations

from fastapi import FastAPI

from app import models  # noqa: F401
from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import get_engine
from app.models.entities import AdminUser
from app.models.entities import ApiClient
from app.models.entities import ApiRequestLog
from app.web.router import web_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    if settings.auto_create_tables:
        Base.metadata.create_all(bind=get_engine())
    else:
        Base.metadata.create_all(
            bind=get_engine(),
            tables=[
                ApiClient.__table__,
                ApiRequestLog.__table__,
                AdminUser.__table__,
            ],
        )

    app.include_router(api_router, prefix=settings.api_prefix)
    app.include_router(web_router)
    return app


app = create_app()
