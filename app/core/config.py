from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    debug: bool
    log_level: str
    api_prefix: str
    host: str
    port: int
    database_url: str
    redis_url: str
    admin_token: str
    auto_create_tables: bool
    max_sources: int
    direct_link_ttl_seconds: int
    direct_link_lock_timeout_seconds: int
    direct_link_wait_seconds: int
    direct_link_retry_base_seconds: int
    scan_poll_interval_seconds: int
    scan_batch_size: int
    source_request_timeout_seconds: int
    opensearch_url: str
    opensearch_index_name: str
    opensearch_timeout_seconds: int
    search_sync_batch_size: int
    preheat_enabled: bool
    preheat_poll_interval_seconds: int
    preheat_limit: int
    preheat_min_hot_score: int
    preheat_refresh_before_seconds: int
    jwt_secret_key: str
    jwt_algorithm: str
    admin_jwt_expire_minutes: int
    download_token_secret: str
    download_token_expire_seconds: int
    public_base_url: str
    download_fallback_redirect: bool


@lru_cache()
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "Unified Library API"),
        app_env=os.getenv("APP_ENV", "development"),
        debug=_get_bool("DEBUG", False),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        api_prefix=os.getenv("API_PREFIX", "/api"),
        host=os.getenv("HOST", "0.0.0.0"),
        port=_get_int("PORT", 8000),
        database_url=os.getenv(
            "DATABASE_URL",
            "sqlite:///./unified_library.db",
        ),
        redis_url=os.getenv("REDIS_URL", ""),
        admin_token=os.getenv("ADMIN_TOKEN", ""),
        auto_create_tables=_get_bool("AUTO_CREATE_TABLES", False),
        max_sources=_get_int("MAX_SOURCES", 5),
        direct_link_ttl_seconds=_get_int("DIRECT_LINK_TTL_SECONDS", 1800),
        direct_link_lock_timeout_seconds=_get_int(
            "DIRECT_LINK_LOCK_TIMEOUT_SECONDS", 30
        ),
        direct_link_wait_seconds=_get_int("DIRECT_LINK_WAIT_SECONDS", 15),
        direct_link_retry_base_seconds=_get_int(
            "DIRECT_LINK_RETRY_BASE_SECONDS", 30
        ),
        scan_poll_interval_seconds=_get_int("SCAN_POLL_INTERVAL_SECONDS", 5),
        scan_batch_size=_get_int("SCAN_BATCH_SIZE", 200),
        source_request_timeout_seconds=_get_int(
            "SOURCE_REQUEST_TIMEOUT_SECONDS", 20
        ),
        opensearch_url=os.getenv("OPENSEARCH_URL", ""),
        opensearch_index_name=os.getenv(
            "OPENSEARCH_INDEX_NAME", "unified_library_files"
        ),
        opensearch_timeout_seconds=_get_int("OPENSEARCH_TIMEOUT_SECONDS", 10),
        search_sync_batch_size=_get_int("SEARCH_SYNC_BATCH_SIZE", 500),
        preheat_enabled=_get_bool("PREHEAT_ENABLED", True),
        preheat_poll_interval_seconds=_get_int(
            "PREHEAT_POLL_INTERVAL_SECONDS", 120
        ),
        preheat_limit=_get_int("PREHEAT_LIMIT", 50),
        preheat_min_hot_score=_get_int("PREHEAT_MIN_HOT_SCORE", 1),
        preheat_refresh_before_seconds=_get_int(
            "PREHEAT_REFRESH_BEFORE_SECONDS", 300
        ),
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", "change-me-jwt-secret"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        admin_jwt_expire_minutes=_get_int("ADMIN_JWT_EXPIRE_MINUTES", 120),
        download_token_secret=os.getenv(
            "DOWNLOAD_TOKEN_SECRET", "change-me-download-secret"
        ),
        download_token_expire_seconds=_get_int(
            "DOWNLOAD_TOKEN_EXPIRE_SECONDS", 600
        ),
        public_base_url=os.getenv("PUBLIC_BASE_URL", ""),
        download_fallback_redirect=_get_bool(
            "DOWNLOAD_FALLBACK_REDIRECT", True
        ),
    )
