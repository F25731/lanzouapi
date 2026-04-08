from __future__ import annotations

import os


def normalize_name(name: str) -> str:
    return " ".join((name or "").strip().lower().split())


def extract_extension(name: str) -> str:
    _, ext = os.path.splitext(name or "")
    return ext.lstrip(".").lower()
