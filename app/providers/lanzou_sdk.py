from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from importlib import import_module
from pathlib import PurePosixPath
from threading import Lock
from typing import Any
from typing import Optional

from app.models.entities import File
from app.models.entities import SourceSource
from app.providers.base import DirectLinkResult
from app.providers.base import FolderListing
from app.providers.base import RemoteFile
from app.providers.base import RemoteFolder
from app.providers.base import SourceProvider
from app.utils.serialization import loads_json


_SIZE_UNITS = {
    "B": 1,
    "BYTE": 1,
    "BYTES": 1,
    "K": 1024,
    "KB": 1024,
    "M": 1024**2,
    "MB": 1024**2,
    "G": 1024**3,
    "GB": 1024**3,
    "T": 1024**4,
    "TB": 1024**4,
}


@dataclass
class _SdkClientState:
    fingerprint: str
    client: Any


class LanzouSdkProvider(SourceProvider):
    adapter_type = "lanzou_sdk"

    def __init__(self) -> None:
        self._clients: dict[int, _SdkClientState] = {}
        self._lock = Lock()

    def login(self, source: SourceSource) -> None:
        self._get_client(source, force_refresh=True)

    def list_folder(
        self,
        source: SourceSource,
        folder_id: Optional[str],
        cursor: Optional[str] = None,
    ) -> FolderListing:
        del cursor
        client = self._get_client(source)
        current_folder_id = self._normalize_folder_id(folder_id or source.root_folder_id)
        current_path = self._folder_path(client, current_folder_id)
        fetch_share_urls = self._config(source).get("fetch_share_urls", True)

        folders = []
        for item in client.get_dir_list(current_folder_id):
            full_path = self._folder_path(client, getattr(item, "id", -1))
            folders.append(
                RemoteFolder(
                    provider_folder_id=str(getattr(item, "id")),
                    name=str(getattr(item, "name")),
                    full_path=full_path,
                    share_url=(
                        self._share_url(client, getattr(item, "id"), is_file=False)
                        if fetch_share_urls
                        else None
                    ),
                    depth=_path_depth(full_path),
                )
            )

        files = []
        for item in client.get_file_list(current_folder_id):
            file_name = str(getattr(item, "name"))
            files.append(
                RemoteFile(
                    provider_file_id=str(getattr(item, "id")),
                    file_name=file_name,
                    file_path=_join_path(current_path, file_name),
                    size_bytes=_parse_size_to_bytes(getattr(item, "size", None)),
                    share_url=(
                        self._share_url(client, getattr(item, "id"), is_file=True)
                        if fetch_share_urls
                        else None
                    ),
                    updated_at=_parse_sdk_date(getattr(item, "time", None)),
                )
            )

        return FolderListing(folders=folders, files=files, next_cursor=None)

    def resolve_direct_link(
        self,
        source: SourceSource,
        file_record: File,
    ) -> DirectLinkResult:
        client = self._get_client(source)
        result = client.get_durl_by_id(int(file_record.provider_file_id))
        code = getattr(result, "code", None)
        success_code = getattr(client, "SUCCESS", 0)
        direct_url = getattr(result, "durl", "") or ""
        if code != success_code or not direct_url:
            raise ValueError(self._code_message(client, code, "解析下载直链失败"))
        return DirectLinkResult(direct_url=direct_url, expires_at=None)

    def _get_client(self, source: SourceSource, force_refresh: bool = False) -> Any:
        fingerprint = self._fingerprint(source)
        with self._lock:
            current = self._clients.get(source.id)
            if (
                not force_refresh
                and current is not None
                and current.fingerprint == fingerprint
            ):
                return current.client

            client = self._build_authenticated_client(source)
            self._clients[source.id] = _SdkClientState(
                fingerprint=fingerprint,
                client=client,
            )
            return client

    def _build_authenticated_client(self, source: SourceSource) -> Any:
        sdk_cls = _load_sdk_class()
        client = sdk_cls()
        config = self._config(source)
        cookie = _extract_cookie(config)

        if cookie:
            result = client.login_by_cookie(cookie)
            if result == getattr(client, "SUCCESS", 0):
                return client

        username = (source.username or "").strip()
        password = source.password or ""
        if username and password:
            result = client.login(username, password)
            if result == getattr(client, "SUCCESS", 0):
                return client
            raise ValueError(
                self._code_message(
                    client,
                    result,
                    "账号密码登录失败，建议改用 Cookie 登录",
                )
            )

        if cookie:
            raise ValueError("Cookie 登录失败，请检查 ylogin 和 phpdisk_info 是否完整有效")

        raise ValueError("lanzou_sdk 需要提供 Cookie，或至少填写账号和密码")

    def _config(self, source: SourceSource) -> dict:
        return loads_json(source.config_json, {})

    def _fingerprint(self, source: SourceSource) -> str:
        config = self._config(source)
        return json.dumps(
            {
                "adapter_type": source.adapter_type,
                "username": source.username or "",
                "password": source.password or "",
                "root_folder_id": source.root_folder_id or "",
                "config": config,
            },
            sort_keys=True,
            ensure_ascii=False,
        )

    def _normalize_folder_id(self, folder_id: Optional[str]) -> int:
        if folder_id in (None, "", "root"):
            return -1
        return int(folder_id)

    def _folder_path(self, client: Any, folder_id: int) -> str:
        if folder_id in (-1, 0):
            return "/"

        try:
            path_items = client.get_full_path(folder_id)
        except Exception:
            return "/"

        names = []
        for item in path_items or []:
            item_id = getattr(item, "id", None)
            item_name = getattr(item, "name", "")
            if item_id in (-1, 0) or not item_name:
                continue
            names.append(str(item_name))

        if not names:
            return "/"
        return "/" + "/".join(names)

    def _share_url(self, client: Any, target_id: Any, is_file: bool) -> Optional[str]:
        info = client.get_share_info(target_id, is_file=is_file)
        success_code = getattr(client, "SUCCESS", 0)
        if getattr(info, "code", None) != success_code:
            return None
        return getattr(info, "url", None)

    def _code_message(self, client: Any, code: Any, fallback: str) -> str:
        code_map = {
            getattr(client, "FAILED", -1): fallback,
            getattr(client, "ID_ERROR", 1): "蓝奏返回了无效的文件或目录 ID",
            getattr(client, "PASSWORD_ERROR", 2): "蓝奏提取码校验失败",
            getattr(client, "LACK_PASSWORD", 3): "蓝奏返回了缺少提取码",
            getattr(client, "URL_INVALID", 6): "蓝奏返回了无效链接",
            getattr(client, "FILE_CANCELLED", 7): "蓝奏文件已失效或被取消分享",
            getattr(client, "NETWORK_ERROR", 9): "连接蓝奏失败，请稍后重试",
            getattr(client, "CAPTCHA_ERROR", 10): "蓝奏触发了验证码校验",
            getattr(client, "OFFICIAL_LIMITED", 11): "蓝奏触发了官方限制，请降低频率后重试",
        }
        return code_map.get(code, f"{fallback} (code={code})")


def _load_sdk_class():
    try:
        module = import_module("lanzou.api")
        return module.LanZouCloud
    except Exception as exc:
        raise RuntimeError(
            "未安装 lanzou-api，请先执行 `pip install lanzou-api` 或重新构建 Docker 镜像"
        ) from exc


def _extract_cookie(config: dict) -> Optional[dict[str, str]]:
    raw_cookie = config.get("cookie")
    if isinstance(raw_cookie, dict):
        cookie = {
            str(key): str(value)
            for key, value in raw_cookie.items()
            if str(value).strip()
        }
        return cookie or None

    if isinstance(raw_cookie, str):
        cookie = {}
        for part in raw_cookie.split(";"):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            if key.strip() and value.strip():
                cookie[key.strip()] = value.strip()
        return cookie or None

    ylogin = str(config.get("ylogin", "") or "").strip()
    phpdisk_info = str(config.get("phpdisk_info", "") or "").strip()
    if ylogin and phpdisk_info:
        return {
            "ylogin": ylogin,
            "phpdisk_info": phpdisk_info,
        }
    return None


def _parse_sdk_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _parse_size_to_bytes(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)

    raw = str(value).strip().replace(",", "")
    match = re.match(r"^([\d.]+)\s*([A-Za-z]+)?$", raw)
    if not match:
        return None

    number = float(match.group(1))
    unit = (match.group(2) or "B").upper()
    multiplier = _SIZE_UNITS.get(unit)
    if multiplier is None:
        return None
    return int(number * multiplier)


def _join_path(prefix: str, name: str) -> str:
    if not prefix or prefix == "/":
        return "/" + name
    return str(PurePosixPath(prefix) / name)


def _path_depth(full_path: str) -> int:
    return len([part for part in PurePosixPath(full_path).parts if part != "/"])
