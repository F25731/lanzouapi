from __future__ import annotations

from typing import List

from app.core.config import get_settings
from app.models.entities import SourceSource
from app.models.enums import SourceStatus
from app.repositories.source_repository import SourceRepository
from app.schemas.source import SourceCreate
from app.schemas.source import SourceUpdate
from app.utils.serialization import dumps_json


class SourceService:
    def __init__(self, source_repository: SourceRepository) -> None:
        self.source_repository = source_repository
        self.settings = get_settings()

    def list_sources(self) -> List[SourceSource]:
        return self.source_repository.list_sources()

    def create_source(self, payload: SourceCreate) -> SourceSource:
        if self.source_repository.count_sources() >= self.settings.max_sources:
            raise ValueError(f"source limit exceeded: max={self.settings.max_sources}")
        if self.source_repository.get_source_by_name(payload.name):
            raise ValueError("source name already exists")

        source = SourceSource(
            name=payload.name,
            adapter_type=payload.adapter_type,
            base_url=payload.base_url,
            username=payload.username,
            password=payload.password,
            root_folder_id=payload.root_folder_id,
            config_json=dumps_json(payload.config),
            status=SourceStatus.ACTIVE,
            is_enabled=True,
            rate_limit_per_minute=payload.rate_limit_per_minute,
            request_timeout_seconds=payload.request_timeout_seconds,
        )
        return self.source_repository.save_source(source)

    def update_source(self, source_id: int, payload: SourceUpdate) -> SourceSource:
        source = self.source_repository.get_source(source_id)
        if source is None:
            raise LookupError("source not found")

        for field_name in [
            "name",
            "adapter_type",
            "base_url",
            "username",
            "password",
            "root_folder_id",
            "rate_limit_per_minute",
            "request_timeout_seconds",
        ]:
            value = getattr(payload, field_name)
            if value is not None:
                setattr(source, field_name, value)

        if payload.config is not None:
            source.config_json = dumps_json(payload.config)

        if payload.is_enabled is not None:
            source.is_enabled = payload.is_enabled
            source.status = (
                SourceStatus.ACTIVE if payload.is_enabled else SourceStatus.DISABLED
            )

        return self.source_repository.save_source(source)

    def disable_source(self, source_id: int) -> SourceSource:
        source = self.source_repository.get_source(source_id)
        if source is None:
            raise LookupError("source not found")
        source.is_enabled = False
        source.status = SourceStatus.DISABLED
        return self.source_repository.save_source(source)
