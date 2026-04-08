from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from typing import Optional

from app.models.entities import File
from app.models.entities import SourceSource
from app.providers.base import DirectLinkResult
from app.providers.base import FolderListing
from app.providers.base import RemoteFile
from app.providers.base import RemoteFolder
from app.providers.base import SourceProvider
from app.utils.serialization import loads_json


class MockSourceProvider(SourceProvider):
    adapter_type = "mock"

    def login(self, source: SourceSource) -> None:
        return None

    def list_folder(
        self,
        source: SourceSource,
        folder_id: Optional[str],
        cursor: Optional[str] = None,
    ) -> FolderListing:
        config = loads_json(source.config_json, {})
        folders_map = config.get("folders", {})
        current_id = folder_id or source.root_folder_id or "root"
        folder_payload = folders_map.get(current_id, {"folders": [], "files": []})

        folders = [
            RemoteFolder(
                provider_folder_id=item["id"],
                name=item["name"],
                full_path=item.get("full_path") or f"/{item['name']}",
                share_url=item.get("share_url"),
                depth=int(item.get("depth", 0)),
            )
            for item in folder_payload.get("folders", [])
        ]
        files = [
            RemoteFile(
                provider_file_id=item["id"],
                file_name=item["name"],
                file_path=item.get("path") or f"/{item['name']}",
                size_bytes=item.get("size_bytes"),
                share_url=item.get("share_url"),
                updated_at=_parse_datetime(item.get("updated_at")),
            )
            for item in folder_payload.get("files", [])
        ]
        return FolderListing(folders=folders, files=files, next_cursor=None)

    def resolve_direct_link(
        self,
        source: SourceSource,
        file_record: File,
    ) -> DirectLinkResult:
        config = loads_json(source.config_json, {})
        direct_links = config.get("direct_links", {})
        direct_url = direct_links.get(file_record.provider_file_id)
        if not direct_url:
            if file_record.share_url:
                direct_url = f"{file_record.share_url}?mock-direct=1"
            else:
                raise ValueError("mock provider missing direct link")
        return DirectLinkResult(
            direct_url=direct_url,
            expires_at=datetime.utcnow() + timedelta(minutes=30),
        )


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value)
