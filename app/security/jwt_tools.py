from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import Optional

import jwt

from app.core.config import get_settings
from app.core.errors import UnauthorizedError


def create_admin_access_token(subject: str, admin_user_id: int) -> str:
    settings = get_settings()
    now = datetime.utcnow()
    payload = {
        "sub": subject,
        "admin_user_id": admin_user_id,
        "type": "admin_access",
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(minutes=settings.admin_jwt_expire_minutes)).timestamp()
        ),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_admin_access_token(token: str) -> Dict:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("invalid admin token") from exc
    if payload.get("type") != "admin_access":
        raise UnauthorizedError("invalid admin token")
    return payload
