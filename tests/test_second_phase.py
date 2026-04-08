from __future__ import annotations


def test_admin_metrics_and_panel(client, seed_mock_file) -> None:
    seed_mock_file("metrics.epub", hot_score=7)

    metrics_response = client.get("/api/admin/metrics")
    assert metrics_response.status_code == 200
    metrics_payload = metrics_response.json()
    assert metrics_payload["file_overview"]["active_files"] == 1
    assert metrics_payload["search_backend"]["backend"] == "database"

    panel_response = client.get("/admin/panel")
    assert panel_response.status_code == 200
    assert "统一书库管理面板" in panel_response.text


def test_preheat_and_reindex_endpoints(client, seed_mock_file) -> None:
    file_id = seed_mock_file("preheat.epub", hot_score=12)

    preheat_response = client.post(
        "/api/admin/preheat",
        json={"limit": 10, "min_hot_score": 1},
    )
    assert preheat_response.status_code == 200
    preheat_payload = preheat_response.json()
    assert preheat_payload["scanned_candidates"] == 1
    assert preheat_payload["refreshed_count"] == 1

    file_response = client.get(f"/api/file/{file_id}")
    assert file_response.status_code == 200
    assert file_response.json()["direct_link_cached"] is True

    reindex_response = client.post(
        "/api/admin/reindex",
        json={"source_id": None, "batch_size": 100},
    )
    assert reindex_response.status_code == 200
    reindex_payload = reindex_response.json()
    assert reindex_payload["backend"] == "database"
    assert reindex_payload["indexed_count"] == 0
