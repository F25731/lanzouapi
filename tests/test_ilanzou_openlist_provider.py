from __future__ import annotations

import json

import httpx

from app.models.entities import File
from app.models.entities import SourceSource
from app.providers.ilanzou_openlist import ILanZouOpenListProvider


def _build_source() -> SourceSource:
    return SourceSource(
        id=7,
        name="ilanzou-main",
        adapter_type="ilanzou_openlist",
        base_url=None,
        username="demo@example.com",
        password="secret",
        root_folder_id="0",
        config_json="{}",
        rate_limit_per_minute=30,
        request_timeout_seconds=20,
    )


def _attach_mock_client(provider, monkeypatch, handler) -> None:
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        provider,
        "_client",
        lambda source: httpx.Client(transport=transport, timeout=20),
    )


def test_ilanzou_openlist_login_and_list_folder(monkeypatch):
    provider = ILanZouOpenListProvider()
    source = _build_source()

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/unproved/getUuid"):
            return httpx.Response(200, json={"uuid": "uuid-1"})
        if path.endswith("/unproved/login"):
            payload = json.loads(request.content.decode("utf-8"))
            assert payload == {"loginName": "demo@example.com", "loginPwd": "secret"}
            return httpx.Response(200, json={"code": 200, "data": {"appToken": "token-1"}})
        if path.endswith("/proved/user/account/map"):
            assert request.url.params["appToken"] == "token-1"
            return httpx.Response(
                200,
                json={"code": 200, "map": {"userId": "user-1", "account": "demo@example.com"}},
            )
        if path.endswith("/proved/record/file/list"):
            assert request.url.params["folderId"] == "0"
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "offset": 1,
                    "totalPage": 1,
                    "list": [
                        {
                            "fileType": 2,
                            "folderId": 200,
                            "folderName": "小说",
                        },
                        {
                            "fileType": 0,
                            "fileId": 300,
                            "fileName": "三体全集.epub",
                            "fileSize": 12064,
                            "updTime": "2026-04-08 12:00:00",
                        },
                    ],
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    _attach_mock_client(provider, monkeypatch, handler)

    provider.login(source)
    listing = provider.list_folder(source, "0")

    assert len(listing.folders) == 1
    assert listing.folders[0].provider_folder_id == "200"
    assert listing.folders[0].full_path == "/小说"
    assert len(listing.files) == 1
    assert listing.files[0].provider_file_id == "300"
    assert listing.files[0].file_path == "/三体全集.epub"
    assert listing.files[0].size_bytes == 12064 * 1024


def test_ilanzou_openlist_resolve_direct_link(monkeypatch):
    provider = ILanZouOpenListProvider()
    source = _build_source()
    file_record = File(provider_file_id="300")

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/unproved/getUuid"):
            return httpx.Response(200, json={"uuid": "uuid-1"})
        if path.endswith("/unproved/login"):
            return httpx.Response(200, json={"code": 200, "data": {"appToken": "token-1"}})
        if path.endswith("/proved/user/account/map"):
            return httpx.Response(
                200,
                json={"code": 200, "map": {"userId": "user-1", "account": "demo@example.com"}},
            )
        if path.endswith("/unproved/file/redirect"):
            assert request.url.params["appToken"] == "token-1"
            assert request.url.params["downloadId"]
            assert request.url.params["auth"]
            return httpx.Response(
                302,
                headers={"location": "https://cdn.ilanzou.com/file-300"},
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    _attach_mock_client(provider, monkeypatch, handler)

    result = provider.resolve_direct_link(source, file_record)
    assert result.direct_url == "https://cdn.ilanzou.com/file-300"


def test_ilanzou_openlist_refreshes_expired_token(monkeypatch):
    provider = ILanZouOpenListProvider()
    source = _build_source()
    login_counter = {"count": 0}
    list_counter = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/unproved/getUuid"):
            return httpx.Response(200, json={"uuid": f"uuid-{login_counter['count'] + 1}"})
        if path.endswith("/unproved/login"):
            login_counter["count"] += 1
            return httpx.Response(
                200,
                json={"code": 200, "data": {"appToken": f"token-{login_counter['count']}"}},
            )
        if path.endswith("/proved/user/account/map"):
            return httpx.Response(
                200,
                json={"code": 200, "map": {"userId": "user-1", "account": "demo@example.com"}},
            )
        if path.endswith("/proved/record/file/list"):
            list_counter["count"] += 1
            if list_counter["count"] == 1:
                return httpx.Response(200, json={"code": -1, "msg": "expired"})
            return httpx.Response(
                200,
                json={"code": 200, "offset": 1, "totalPage": 1, "list": []},
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    _attach_mock_client(provider, monkeypatch, handler)

    listing = provider.list_folder(source, "0")
    assert listing.files == []
    assert listing.folders == []
    assert login_counter["count"] == 2
