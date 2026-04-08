from __future__ import annotations

from fastapi.encoders import jsonable_encoder


def api_success(data=None, message: str = "ok") -> dict:
    return {
        "code": 0,
        "message": message,
        "data": jsonable_encoder(data),
    }


def api_error(code: int, message: str, data=None) -> dict:
    return {
        "code": code,
        "message": message,
        "data": jsonable_encoder(data),
    }
