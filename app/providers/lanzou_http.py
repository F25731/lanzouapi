from __future__ import annotations

from datetime import datetime
from typing import Optional

import httpx

from app.core.config import get_settings
from app.models.entities import File
from app.models.entities import SourceSource
from app.providers.base import DirectLinkResult
from app.providers.base import FolderListing
from app.providers.base import RemoteFile
from app.providers.base import RemoteFolder
from app.providers.base import SourceProvider
from app.utils.serialization import loads_json


class LanzouHttpProvider(SourceProvider):
    adapter_type = "lanzou_http"

    def login(self, source: SourceSource) -> None:
        config = self._config(source)
        login_path = config.get("login_path")
        if not login_path:
            return
        with self._client(source) as client:
            response = client.post(
                login_path,
                json={
                    "username": source.username,
                    "password": source.password,
                },
            )
            response.raise_for_status()

    def list_folder(
        self,
        source: SourceSource,
        folder_id: Optional[str],
        cursor: Optional[str] = None,
    ) -> FolderListing:
        config = self._config(source)
        folder_id = folder_id or source.root_folder_id
        list_root_path = config.get("list_root_path", "/api/folders")
        list_folder_path = config.get("list_folder_path", "/api/folders/{folder_id}")
        endpoint = list_root_path if not folder_id else list_folder_path.format(folder_id=folder_id)

        params = {}
        if cursor:
            params["cursor"] = cursor

        with self._client(source) as client:
            response = client.get(endpoint, params=params or None)
            response.raise_for_status()
            payload = response.json()

        folders = [
            RemoteFolder(
                provider_folder_id=str(item["id"]),
                name=item["name"],
                full_path=item.get("full_path") or f"/{item['name']}",
                share_url=item.get("share_url"),
                depth=int(item.get("depth", 0)),
            )
            for item in payload.get("folders", [])
        ]
        files = [
            RemoteFile(
                provider_file_id=str(item["id"]),
                file_name=item["name"],
                file_path=item.get("path") or f"/{item['name']}",
                size_bytes=item.get("size_bytes"),
                share_url=item.get("share_url"),
                updated_at=_parse_datetime(item.get("updated_at")),
            )
            for item in payload.get("files", [])
        ]
        return FolderListing(
            folders=folders,
            files=files,
            next_cursor=payload.get("next_cursor"),
        )

    def resolve_direct_link(
        self,
        source: SourceSource,
        file_record: File,
    ) -> DirectLinkResult:
        config = self._config(source)
        resolve_path = config.get("resolve_path", "/api/resolve")
        resolve_method = str(config.get("resolve_method", "POST")).upper()
        payload = {
            "file_id": file_record.provider_file_id,
            "share_url": file_record.share_url,
        }

        with self._client(source) as client:
            if resolve_method == "GET":
                response = client.get(resolve_path, params=payload)
            else:
                response = client.post(resolve_path, json=payload)
            response.raise_for_status()
            body = response.json()

        direct_url = body.get("direct_url")
        if not direct_url:
            raise ValueError("provider did not return direct_url")

        return DirectLinkResult(
            direct_url=direct_url,
            expires_at=_parse_datetime(body.get("expires_at")),
        )

    def _client(self, source: SourceSource) -> httpx.Client:
        config = self._config(source)
        headers = config.get("headers", {})
        timeout = source.request_timeout_seconds or get_settings().source_request_timeout_seconds
        if not source.base_url:
            raise ValueError("source.base_url is required for lanzou_http adapter")
        return httpx.Client(
            base_url=source.base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
        )

    def _config(self, source: SourceSource) -> dict:
        return loads_json(source.config_json, {})


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value)
