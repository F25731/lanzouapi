from __future__ import annotations

from typing import Optional

from fastapi import Header
from fastapi import HTTPException
from fastapi import Query
from fastapi import status

from app.core.config import get_settings


def require_admin(
    x_admin_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> None:
    settings = get_settings()
    presented_token = x_admin_token or token
    if settings.admin_token and presented_token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid admin token",
        )
