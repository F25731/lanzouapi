from __future__ import annotations


def _source_payload(index: int) -> dict:
    return {
        "name": f"source-{index}",
        "adapter_type": "mock",
        "username": "demo",
        "password": "demo",
        "config": {},
        "rate_limit_per_minute": 30,
        "request_timeout_seconds": 20,
    }


def test_source_limit_is_enforced(client) -> None:
    for index in range(1, 6):
        response = client.post("/api/admin/sources", json=_source_payload(index))
        assert response.status_code == 200

    overflow = client.post("/api/admin/sources", json=_source_payload(6))
    assert overflow.status_code == 400
    assert "source limit exceeded" in overflow.json()["detail"]
