from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Any
from typing import Optional

import httpx
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.ciphers import modes

from app.models.entities import File
from app.models.entities import SourceSource
from app.providers.base import DirectLinkResult
from app.providers.base import FolderListing
from app.providers.base import RemoteFile
from app.providers.base import RemoteFolder
from app.providers.base import SourceProvider
from app.utils.serialization import loads_json


DEFAULT_API_BASE = "https://api.ilanzou.com"
DEFAULT_SITE_BASE = "https://www.ilanzou.com"
DEFAULT_SECRET = "lanZouY-disk-app"
DEFAULT_DEV_VERSION = "125"
DEFAULT_UNPROVED_PREFIX = "unproved"
DEFAULT_PROVED_PREFIX = "proved"


@dataclass
class _ILanZouState:
    fingerprint: str
    uuid: str
    token: str
    user_id: str
    account: str
    folder_paths: dict[str, str]


class _ILanZouApiError(RuntimeError):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ILanZouOpenListProvider(SourceProvider):
    adapter_type = "ilanzou_openlist"

    def __init__(self) -> None:
        self._states: dict[int, _ILanZouState] = {}
        self._lock = Lock()

    def login(self, source: SourceSource) -> None:
        self._ensure_state(source, force_refresh=True)

    def list_folder(
        self,
        source: SourceSource,
        folder_id: Optional[str],
        cursor: Optional[str] = None,
    ) -> FolderListing:
        del cursor
        state = self._ensure_state(source)
        current_folder_id = str(folder_id or source.root_folder_id or "0")
        current_path = state.folder_paths.get(current_folder_id, "/")
        page = 1
        folders: list[RemoteFolder] = []
        files: list[RemoteFile] = []

        while True:
            body, state = self._request_json_with_refresh(
                source=source,
                state=state,
                path="/record/file/list",
                method="GET",
                proved=True,
                extra_query={
                    "offset": str(page),
                    "limit": "60",
                    "folderId": current_folder_id,
                    "type": "0",
                },
            )

            for item in body.get("list") or []:
                file_type = int(item.get("fileType") or 0)
                if file_type == 2:
                    folder_name = str(
                        item.get("folderName") or item.get("fileName") or "folder"
                    )
                    provider_folder_id = str(
                        item.get("folderId") or item.get("id") or ""
                    )
                    full_path = _join_path(current_path, folder_name)
                    folders.append(
                        RemoteFolder(
                            provider_folder_id=provider_folder_id,
                            name=folder_name,
                            full_path=full_path,
                            share_url=None,
                            depth=_path_depth(full_path),
                        )
                    )
                    if provider_folder_id:
                        state.folder_paths[provider_folder_id] = full_path
                else:
                    file_name = str(item.get("fileName") or "file")
                    files.append(
                        RemoteFile(
                            provider_file_id=str(item.get("fileId") or item.get("id") or ""),
                            file_name=file_name,
                            file_path=_join_path(current_path, file_name),
                            size_bytes=_size_kb_to_bytes(item.get("fileSize")),
                            share_url=None,
                            updated_at=_parse_ilanzou_time(item.get("updTime")),
                        )
                    )

            offset = int(body.get("offset") or page)
            total_page = int(body.get("totalPage") or page)
            if offset >= total_page:
                break
            page += 1

        return FolderListing(folders=folders, files=files, next_cursor=None)

    def resolve_direct_link(
        self,
        source: SourceSource,
        file_record: File,
    ) -> DirectLinkResult:
        state = self._ensure_state(source)
        direct_url, _ = self._resolve_redirect(
            source=source,
            state=state,
            file_id=str(file_record.provider_file_id),
        )
        return DirectLinkResult(direct_url=direct_url, expires_at=None)

    def _ensure_state(
        self,
        source: SourceSource,
        force_refresh: bool = False,
    ) -> _ILanZouState:
        fingerprint = self._fingerprint(source)
        with self._lock:
            cached = self._states.get(source.id)
            if (
                not force_refresh
                and cached is not None
                and cached.fingerprint == fingerprint
            ):
                return cached

        fresh = self._login_state(source)
        with self._lock:
            self._states[source.id] = fresh
        return fresh

    def _login_state(self, source: SourceSource) -> _ILanZouState:
        username = (source.username or "").strip()
        password = source.password or ""
        if not username or not password:
            raise ValueError("ilanzou account/password is required")

        config = self._config(source)
        uuid = str(config.get("uuid") or "").strip() or self._fetch_uuid(source)
        token = self._login_with_password(source, uuid, username, password)
        account_map = self._request_json(
            source=source,
            uuid=uuid,
            token=token,
            path="/user/account/map",
            method="GET",
            proved=True,
            extra_query=None,
            json_body=None,
        )
        info = account_map.get("map") or {}

        return _ILanZouState(
            fingerprint=self._fingerprint(source),
            uuid=uuid,
            token=token,
            user_id=str(info.get("userId") or ""),
            account=str(info.get("account") or username),
            folder_paths={"0": "/", "-1": "/"},
        )

    def _fetch_uuid(self, source: SourceSource) -> str:
        with self._client(source) as client:
            response = client.get(
                self._build_url(source, proved=False, path="/getUuid"),
                params=self._signed_query(source=source, uuid="", token=None),
                headers=self._headers(source),
            )
            response.raise_for_status()
            body = response.json()
        uuid = str(body.get("uuid") or "").strip()
        if not uuid:
            raise ValueError("ilanzou login failed: uuid is empty")
        return uuid

    def _login_with_password(
        self,
        source: SourceSource,
        uuid: str,
        username: str,
        password: str,
    ) -> str:
        body = self._request_json(
            source=source,
            uuid=uuid,
            token=None,
            path="/login",
            method="POST",
            proved=False,
            extra_query=None,
            json_body={
                "loginName": username,
                "loginPwd": password,
            },
        )
        token = str((body.get("data") or {}).get("appToken") or "").strip()
        if not token:
            raise ValueError("ilanzou login failed: appToken is empty")
        return token

    def _request_json_with_refresh(
        self,
        source: SourceSource,
        state: _ILanZouState,
        path: str,
        method: str,
        proved: bool,
        extra_query: Optional[dict[str, str]],
        json_body: Optional[dict[str, Any]] = None,
        retry: bool = False,
    ) -> tuple[dict[str, Any], _ILanZouState]:
        try:
            body = self._request_json(
                source=source,
                uuid=state.uuid,
                token=state.token,
                path=path,
                method=method,
                proved=proved,
                extra_query=extra_query,
                json_body=json_body,
            )
            return body, state
        except _ILanZouApiError as exc:
            if not retry and exc.code in (-1, -2):
                fresh = self._ensure_state(source, force_refresh=True)
                return self._request_json_with_refresh(
                    source=source,
                    state=fresh,
                    path=path,
                    method=method,
                    proved=proved,
                    extra_query=extra_query,
                    json_body=json_body,
                    retry=True,
                )
            raise ValueError(f"ilanzou request failed: {exc.message}") from exc

    def _request_json(
        self,
        source: SourceSource,
        uuid: str,
        token: Optional[str],
        path: str,
        method: str,
        proved: bool,
        extra_query: Optional[dict[str, str]],
        json_body: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        with self._client(source) as client:
            response = client.request(
                method,
                self._build_url(source, proved=proved, path=path),
                params=self._signed_query(
                    source=source,
                    uuid=uuid,
                    token=token,
                    extra=extra_query,
                ),
                json=json_body,
                headers=self._headers(source),
            )
            response.raise_for_status()
            body = response.json()

        code = int(body.get("code") or 0)
        if code != 200:
            raise _ILanZouApiError(code, str(body.get("msg") or "unknown error"))
        return body

    def _resolve_redirect(
        self,
        source: SourceSource,
        state: _ILanZouState,
        file_id: str,
        retry: bool = False,
    ) -> tuple[str, _ILanZouState]:
        query = self._redirect_query(source, state, file_id)

        with self._client(source) as client:
            response = client.get(
                self._build_url(source, proved=False, path="/file/redirect"),
                params=query,
                headers=self._headers(source),
                follow_redirects=False,
            )

        if response.status_code == 302:
            location = response.headers.get("location")
            if not location:
                raise ValueError("ilanzou redirect failed: location header is empty")
            return location, state

        try:
            body = response.json()
        except ValueError as exc:
            response.raise_for_status()
            raise ValueError(
                f"ilanzou redirect failed: unexpected HTTP {response.status_code}"
            ) from exc

        code = int(body.get("code") or 0)
        if not retry and code in (-1, -2):
            fresh = self._ensure_state(source, force_refresh=True)
            return self._resolve_redirect(source, fresh, file_id, retry=True)

        raise ValueError(
            str(body.get("msg") or f"ilanzou redirect failed: HTTP {response.status_code}")
        )

    def _redirect_query(
        self,
        source: SourceSource,
        state: _ILanZouState,
        file_id: str,
    ) -> dict[str, str]:
        config = self._config(source)
        secret = str(config.get("secret") or DEFAULT_SECRET)
        timestamp_raw = _unix_ms()
        return self._signed_query(
            source=source,
            uuid=state.uuid,
            token=state.token,
            extra={
                "enable": "0",
                "downloadId": _aes_ecb_hex(f"{file_id}|{state.user_id}", secret),
                "auth": _aes_ecb_hex(f"{file_id}|{timestamp_raw}", secret),
            },
        )

    def _signed_query(
        self,
        source: SourceSource,
        uuid: str,
        token: Optional[str],
        extra: Optional[dict[str, str]] = None,
    ) -> dict[str, str]:
        config = self._config(source)
        secret = str(config.get("secret") or DEFAULT_SECRET)
        query = {
            "uuid": uuid,
            "devType": "6",
            "devCode": uuid,
            "devModel": "chrome",
            "devVersion": str(config.get("dev_version") or DEFAULT_DEV_VERSION),
            "appVersion": "",
            "timestamp": _aes_ecb_hex(str(_unix_ms()), secret),
            "extra": "2",
        }
        if token:
            query["appToken"] = token
        if extra:
            query.update(extra)
        return query

    def _build_url(self, source: SourceSource, proved: bool, path: str) -> str:
        config = self._config(source)
        base_url = str(
            source.base_url
            or config.get("api_base")
            or DEFAULT_API_BASE
        ).rstrip("/")
        prefix = str(
            config.get("proved_prefix" if proved else "unproved_prefix")
            or (DEFAULT_PROVED_PREFIX if proved else DEFAULT_UNPROVED_PREFIX)
        ).strip("/")
        return f"{base_url}/{prefix}/{path.lstrip('/')}"

    def _headers(self, source: SourceSource) -> dict[str, str]:
        config = self._config(source)
        site_base = str(config.get("site_base") or DEFAULT_SITE_BASE).rstrip("/")
        headers = {
            "Origin": site_base,
            "Referer": site_base + "/",
            "Accept-Encoding": "gzip",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US,en;q=0.8",
            "User-Agent": str(
                config.get("user_agent")
                or (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            ),
        }
        forwarded_ip = str(config.get("forwarded_ip") or "").strip()
        if forwarded_ip:
            headers["X-Forwarded-For"] = forwarded_ip
        return headers

    def _client(self, source: SourceSource) -> httpx.Client:
        return httpx.Client(timeout=source.request_timeout_seconds or 20)

    def _config(self, source: SourceSource) -> dict[str, Any]:
        return loads_json(source.config_json, {})

    def _fingerprint(self, source: SourceSource) -> str:
        config = self._config(source)
        parts = [
            source.adapter_type,
            source.base_url or "",
            source.username or "",
            source.password or "",
            source.root_folder_id or "",
            str(config.get("api_base") or ""),
            str(config.get("site_base") or ""),
            str(config.get("secret") or ""),
            str(config.get("dev_version") or ""),
            str(config.get("forwarded_ip") or ""),
        ]
        return "|".join(parts)


def _aes_ecb_hex(raw: str, secret: str) -> str:
    padder = padding.PKCS7(128).padder()
    padded = padder.update(raw.encode("utf-8")) + padder.finalize()
    cipher = Cipher(algorithms.AES(secret.encode("utf-8")), modes.ECB())
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return encrypted.hex()


def _unix_ms() -> int:
    return int(datetime.utcnow().timestamp() * 1000)


def _size_kb_to_bytes(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value) * 1024
    except (TypeError, ValueError):
        return None


def _parse_ilanzou_time(value: Any) -> Optional[datetime]:
    if not value:
        return None
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _join_path(prefix: str, name: str) -> str:
    clean_prefix = prefix or "/"
    if clean_prefix == "/":
        return "/" + name
    return clean_prefix.rstrip("/") + "/" + name


def _path_depth(path: str) -> int:
    return len([part for part in path.split("/") if part])
