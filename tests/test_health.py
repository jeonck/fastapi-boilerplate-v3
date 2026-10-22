"""
Test Health API endpoints.

This module contains tests for health check and system status endpoints.
"""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test the main health check endpoint."""
    response = client.get("/api/health/")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data
    assert "environment" in data


def test_ping(client: TestClient):
    """Test the ping endpoint."""
    response = client.get("/api/health/ping")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["message"] == "pong"
    assert "data" in data
    assert "timestamp" in data["data"]


def test_app_info(client: TestClient):
    """Test the application info endpoint."""
    response = client.get("/api/health/info")
    assert response.status_code == 200

    data = response.json()
    assert "app_name" in data
    assert "version" in data
    assert "description" in data
    assert "environment" in data
    assert "debug" in data
    assert data["docs_url"] == "/docs"
    assert data["redoc_url"] == "/redoc"
