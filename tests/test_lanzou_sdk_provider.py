from __future__ import annotations

from collections import namedtuple

from app.models.entities import File
from app.models.entities import SourceSource
from app.providers.lanzou_sdk import LanzouSdkProvider
from app.utils.serialization import dumps_json


Folder = namedtuple("Folder", ["name", "id", "has_pwd", "desc"])
FolderId = namedtuple("FolderId", ["name", "id"])
FileItem = namedtuple(
    "FileItem",
    ["name", "id", "time", "size", "type", "downs", "has_pwd", "has_des"],
)
ShareInfo = namedtuple("ShareInfo", ["code", "name", "url", "pwd", "desc"])
DirectUrlInfo = namedtuple("DirectUrlInfo", ["code", "name", "durl"])


class FakeLanZouCloud:
    SUCCESS = 0
    FAILED = -1
    NETWORK_ERROR = 9

    def __init__(self) -> None:
        self.logged_in = False

    def login_by_cookie(self, cookie: dict) -> int:
        self.logged_in = cookie.get("ylogin") == "10001"
        return self.SUCCESS if self.logged_in else self.FAILED

    def login(self, username: str, password: str) -> int:
        self.logged_in = username == "demo" and password == "demo"
        return self.SUCCESS if self.logged_in else self.FAILED

    def get_dir_list(self, folder_id=-1):
        assert self.logged_in is True
        if folder_id == -1:
            return [Folder("小说", 10, False, "")]
        return []

    def get_file_list(self, folder_id=-1):
        assert self.logged_in is True
        if folder_id == -1:
            return [
                FileItem(
                    "三体全集.epub",
                    501,
                    "2026-04-08",
                    "12.0M",
                    "epub",
                    0,
                    False,
                    False,
                )
            ]
        return [
            FileItem(
                "盗墓笔记.zip",
                502,
                "2026-04-07",
                "2.5G",
                "zip",
                0,
                False,
                False,
            )
        ]

    def get_full_path(self, folder_id=-1):
        if folder_id == 10:
            return [FolderId("LanZouCloud", -1), FolderId("小说", 10)]
        return [FolderId("LanZouCloud", -1)]

    def get_share_info(self, fid, is_file=True):
        prefix = "file" if is_file else "folder"
        return ShareInfo(
            self.SUCCESS,
            f"{prefix}-{fid}",
            f"https://share.example.com/{prefix}/{fid}",
            "",
            "",
        )

    def get_durl_by_id(self, fid):
        return DirectUrlInfo(self.SUCCESS, f"file-{fid}", f"https://download.example.com/{fid}")


def _build_source(config: dict | None = None, username: str = "", password: str = "") -> SourceSource:
    return SourceSource(
        id=1,
        name="lanzou-main",
        adapter_type="lanzou_sdk",
        base_url=None,
        username=username,
        password=password,
        root_folder_id=None,
        config_json=dumps_json(config or {}),
        is_enabled=True,
        rate_limit_per_minute=30,
        request_timeout_seconds=20,
    )


def test_lanzou_sdk_provider_supports_cookie_login(monkeypatch):
    monkeypatch.setattr(
        "app.providers.lanzou_sdk._load_sdk_class",
        lambda: FakeLanZouCloud,
    )
    provider = LanzouSdkProvider()
    source = _build_source({"cookie": {"ylogin": "10001", "phpdisk_info": "token-abc"}})

    provider.login(source)
    listing = provider.list_folder(source, folder_id=None)

    assert len(listing.folders) == 1
    assert listing.folders[0].provider_folder_id == "10"
    assert listing.folders[0].full_path == "/小说"
    assert len(listing.files) == 1
    assert listing.files[0].file_name == "三体全集.epub"
    assert listing.files[0].file_path == "/三体全集.epub"
    assert listing.files[0].size_bytes == 12 * 1024 * 1024


def test_lanzou_sdk_provider_resolves_direct_link(monkeypatch):
    monkeypatch.setattr(
        "app.providers.lanzou_sdk._load_sdk_class",
        lambda: FakeLanZouCloud,
    )
    provider = LanzouSdkProvider()
    source = _build_source({"cookie": {"ylogin": "10001", "phpdisk_info": "token-abc"}})
    file_record = File(
        id=99,
        source=source,
        provider_file_id="502",
        file_name="盗墓笔记.zip",
        file_path="/小说/盗墓笔记.zip",
        share_url="https://share.example.com/file/502",
    )

    result = provider.resolve_direct_link(source, file_record)

    assert result.direct_url == "https://download.example.com/502"


def test_lanzou_sdk_provider_can_fallback_to_password_login(monkeypatch):
    monkeypatch.setattr(
        "app.providers.lanzou_sdk._load_sdk_class",
        lambda: FakeLanZouCloud,
    )
    provider = LanzouSdkProvider()
    source = _build_source({}, username="demo", password="demo")

    provider.login(source)
    listing = provider.list_folder(source, folder_id="10")

    assert len(listing.files) == 1
    assert listing.files[0].file_path == "/小说/盗墓笔记.zip"
    assert listing.files[0].size_bytes == int(2.5 * 1024 * 1024 * 1024)
