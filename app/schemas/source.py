from __future__ import annotations

from datetime import datetime
from typing import Dict
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from app.models.entities import SourceSource
from app.utils.serialization import loads_json


class SourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    adapter_type: str = Field(default="lanzou_http", max_length=50)
    base_url: Optional[str] = None
    username: str = Field(default="", max_length=120)
    password: str = Field(default="", max_length=255)
    root_folder_id: Optional[str] = Field(default=None, max_length=120)
    config: Dict = Field(default_factory=dict)
    rate_limit_per_minute: int = Field(default=30, ge=1, le=600)
    request_timeout_seconds: int = Field(default=20, ge=1, le=120)


class SourceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    adapter_type: Optional[str] = Field(default=None, max_length=50)
    base_url: Optional[str] = None
    username: Optional[str] = Field(default=None, max_length=120)
    password: Optional[str] = Field(default=None, max_length=255)
    root_folder_id: Optional[str] = Field(default=None, max_length=120)
    config: Optional[Dict] = None
    is_enabled: Optional[bool] = None
    rate_limit_per_minute: Optional[int] = Field(default=None, ge=1, le=600)
    request_timeout_seconds: Optional[int] = Field(default=None, ge=1, le=120)


class SourceRead(BaseModel):
    id: int
    name: str
    adapter_type: str
    base_url: Optional[str]
    username: str
    root_folder_id: Optional[str]
    config: Dict
    status: str
    is_enabled: bool
    rate_limit_per_minute: int
    request_timeout_seconds: int
    last_login_at: Optional[datetime]
    last_sync_at: Optional[datetime]
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, source: SourceSource) -> "SourceRead":
        return cls(
            id=source.id,
            name=source.name,
            adapter_type=source.adapter_type,
            base_url=source.base_url,
            username=source.username,
            root_folder_id=source.root_folder_id,
            config=loads_json(source.config_json, {}),
            status=source.status.value,
            is_enabled=source.is_enabled,
            rate_limit_per_minute=source.rate_limit_per_minute,
            request_timeout_seconds=source.request_timeout_seconds,
            last_login_at=source.last_login_at,
            last_sync_at=source.last_sync_at,
            last_error=source.last_error,
            created_at=source.created_at,
            updated_at=source.updated_at,
        )
