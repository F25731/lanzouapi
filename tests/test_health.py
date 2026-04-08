from __future__ import annotations


def test_health_endpoint(client) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["database"] == "ok"
    assert payload["status"] in {"ok", "degraded"}
