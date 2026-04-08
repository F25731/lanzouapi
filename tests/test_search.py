from __future__ import annotations


def test_search_returns_seeded_file(client, seed_mock_file) -> None:
    seed_mock_file("novel.epub")

    response = client.post(
        "/api/search",
        json={
            "keyword": "novel",
            "page": 1,
            "size": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["backend"] == "database"
    assert payload["total"] == 1
    assert payload["items"][0]["file_name"] == "novel.epub"
