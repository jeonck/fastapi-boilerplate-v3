"""
Test Response Caching (FastAPI-Cache).
"""

from fastapi.testclient import TestClient


def test_cached_endpoint(client: TestClient):
    """The second call is served from the cache with the same payload."""
    first = client.get("/api/demo/cached")
    second = client.get("/api/demo/cached")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.headers["X-FastAPI-Cache"] == "HIT"
    assert first.json()["computed_at"] == second.json()["computed_at"]


def test_item_stats_cache_invalidation(client: TestClient, auth_headers, sample_item_data):
    """Item stats are cached and invalidated when items change."""
    before = client.get("/api/stats/items")
    assert before.status_code == 200
    assert client.get("/api/stats/items").headers["X-FastAPI-Cache"] == "HIT"

    # Creating an item clears the "items" cache namespace
    client.post("/api/items", json=sample_item_data, headers=auth_headers)

    after = client.get("/api/stats/items")
    assert after.headers["X-FastAPI-Cache"] == "MISS"
    assert after.json()["total_items"] == before.json()["total_items"] + 1


def test_clear_cache_requires_superuser(client: TestClient, auth_headers):
    """Only superusers can clear the whole cache."""
    assert client.delete("/api/demo/cache").status_code == 401
    assert client.delete("/api/demo/cache", headers=auth_headers).status_code == 403
