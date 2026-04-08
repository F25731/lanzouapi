from __future__ import annotations


def test_source_login_test_endpoint(client):
    create_response = client.post(
        "/api/admin/sources",
        json={
            "name": "mock-login-source",
            "adapter_type": "mock",
            "base_url": "https://example.com",
            "username": "demo",
            "password": "demo",
            "root_folder_id": "root",
            "config": {},
            "rate_limit_per_minute": 30,
            "request_timeout_seconds": 20,
        },
    )
    assert create_response.status_code == 200
    source_id = create_response.json()["id"]

    login_response = client.post(f"/api/admin/source/{source_id}/login-test")
    assert login_response.status_code == 200
    body = login_response.json()
    assert body["id"] == source_id
    assert body["success"] is True
    assert body["status"] == "active"


def test_api_client_management_endpoints(client):
    create_response = client.post(
        "/api/admin/api-client/create",
        json={
            "client_name": "robot-main",
            "client_type": "robot",
            "rate_limit_per_min": 60,
            "ip_whitelist": ["127.0.0.1"],
        },
    )
    assert create_response.status_code == 200
    body = create_response.json()
    assert body["client"]["client_name"] == "robot-main"
    assert body["client"]["status"] == "active"
    assert body["api_key"].startswith("uk_")

    list_response = client.get("/api/admin/api-clients")
    assert list_response.status_code == 200
    clients = list_response.json()
    assert len(clients) == 1
    client_id = clients[0]["id"]

    disable_response = client.post(f"/api/admin/api-client/{client_id}/disable")
    assert disable_response.status_code == 200
    assert disable_response.json()["status"] == "disabled"

    rotate_response = client.post(f"/api/admin/api-client/{client_id}/rotate")
    assert rotate_response.status_code == 200
    assert rotate_response.json()["api_key"].startswith("uk_")
