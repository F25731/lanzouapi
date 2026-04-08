from __future__ import annotations

import secrets
from typing import Tuple


def generate_api_key() -> Tuple[str, str]:
    public = "uk_{0}".format(secrets.token_urlsafe(6).replace("-", "").replace("_", ""))
    secret = secrets.token_urlsafe(32)
    full_key = "{0}.{1}".format(public, secret)
    return public, full_key


def extract_key_prefix(api_key: str) -> str:
    if "." not in api_key:
        return ""
    return api_key.split(".", 1)[0]
