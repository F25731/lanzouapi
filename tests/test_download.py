from __future__ import annotations


def test_download_uses_cache_after_first_resolution(client, seed_mock_file) -> None:
    file_id = seed_mock_file()

    first_response = client.get(f"/api/download/{file_id}", follow_redirects=False)
    second_response = client.get(f"/api/download/{file_id}", follow_redirects=False)

    assert first_response.status_code == 302
    assert first_response.headers["location"] == "https://cdn.example.com/book.epub"
    assert first_response.headers["x-download-cache"] == "miss"

    assert second_response.status_code == 302
    assert second_response.headers["location"] == "https://cdn.example.com/book.epub"
    assert second_response.headers["x-download-cache"] == "hit"
