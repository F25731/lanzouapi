from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware

from app.db.session import session_scope
from app.repositories.auth_repository import ApiRequestLogRepository


logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            status_code = response.status_code if response is not None else 500
            client = getattr(request.state, "api_client", None)
            request_ip = request.client.host if request.client else None

            try:
                with session_scope() as db:
                    ApiRequestLogRepository(db).create_log(
                        client_id=client.id if client else None,
                        request_path=request.url.path,
                        request_method=request.method,
                        request_ip=request_ip,
                        status_code=status_code,
                        latency_ms=latency_ms,
                    )
            except Exception:
                logger.exception("failed to persist request log")
