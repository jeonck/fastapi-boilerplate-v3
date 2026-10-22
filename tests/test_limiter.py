"""
Test Rate Limiting (FastAPI-Limiter).
"""

import uuid

from fastapi.testclient import TestClient


def test_rate_limit_exceeded(client: TestClient):
    """The demo endpoint allows 5 requests per 60s per client."""
    # Use a unique client IP so other tests do not share the bucket
    headers = {"X-Forwarded-For": f"10.0.0.{uuid.uuid4().int % 250}-{uuid.uuid4().hex}"}

    for _ in range(5):
        response = client.get("/api/demo/limited", headers=headers)
        assert response.status_code == 200

    response = client.get("/api/demo/limited", headers=headers)
    assert response.status_code == 429
    assert response.json()["detail"] == "Too Many Requests"


def test_rate_limit_is_per_client(client: TestClient):
    """Another client is not affected by someone else's limit."""
    blocked = {"X-Forwarded-For": f"blocked-{uuid.uuid4().hex}"}
    for _ in range(6):
        client.get("/api/demo/limited", headers=blocked)

    other = {"X-Forwarded-For": f"other-{uuid.uuid4().hex}"}
    response = client.get("/api/demo/limited", headers=other)
    assert response.status_code == 200
