from __future__ import annotations

from typing import List

from app.utils.serialization import dumps_json
from app.utils.serialization import loads_json


def parse_scopes(raw: str | None) -> List[str]:
    values = loads_json(raw, None)
    if isinstance(values, list):
        return [str(item).strip() for item in values if str(item).strip()]
    if raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    return []


def dump_scopes(values: List[str]) -> str:
    normalized = sorted(set(item.strip() for item in values if item.strip()))
    return dumps_json(normalized)


def parse_ip_whitelist(raw: str | None) -> List[str]:
    values = loads_json(raw, None)
    if isinstance(values, list):
        return [str(item).strip() for item in values if str(item).strip()]
    if raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    return []


def dump_ip_whitelist(values: List[str]) -> str:
    normalized = sorted(set(item.strip() for item in values if item.strip()))
    return dumps_json(normalized)
