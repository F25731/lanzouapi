from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from typing import Dict

import jwt

from app.core.config import get_settings
from app.core.errors import UnauthorizedError


def create_download_token(file_id: int) -> str:
    settings = get_settings()
    now = datetime.utcnow()
    payload = {
        "file_id": file_id,
        "type": "download",
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(seconds=settings.download_token_expire_seconds)).timestamp()
        ),
    }
    return jwt.encode(
        payload,
        settings.download_token_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_download_token(token: str) -> Dict:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.download_token_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("invalid download token", code=40110) from exc
    if payload.get("type") != "download":
        raise UnauthorizedError("invalid download token", code=40110)
    return payload
