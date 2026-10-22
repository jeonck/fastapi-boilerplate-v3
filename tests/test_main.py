"""
Test Main Application.

This module contains tests for the main application endpoints
and template rendering.
"""

from fastapi.testclient import TestClient


def test_read_root(client: TestClient):
    """Test the root endpoint returns HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    # Check if the response contains expected content
    content = response.text
    assert "FastAPI Boilerplate v3" in content
    assert "FastAPI Users" in content
    assert "CrudRouter" in content
    assert "Limiter" in content
    assert "Cache" in content
    assert "/docs" in content
    assert "/redoc" in content


def test_favicon(client: TestClient):
    """Test the favicon endpoint."""
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert "message" in response.json()


def test_not_found_handler(client: TestClient):
    """Test the custom 404 handler."""
    response = client.get("/nonexistent-endpoint")
    assert response.status_code == 404
    # The 404 handler returns HTML template
    assert "text/html" in response.headers["content-type"]


def test_api_not_found_returns_json(client: TestClient):
    """Test that unknown API paths return JSON 404."""
    response = client.get("/api/nonexistent-endpoint")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_api_documentation_accessible(client: TestClient):
    """Test that API documentation endpoints are accessible."""
    docs_response = client.get("/docs")
    assert docs_response.status_code == 200
    assert "text/html" in docs_response.headers["content-type"]

    redoc_response = client.get("/redoc")
    assert redoc_response.status_code == 200
    assert "text/html" in redoc_response.headers["content-type"]


def test_openapi_schema(client: TestClient):
    """Test that OpenAPI schema is available and lists all feature routes."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert schema["info"]["title"] == "FastAPI Boilerplate v3"
    paths = schema["paths"]
    assert "/api/auth/jwt/login" in paths
    assert "/api/auth/register" in paths
    assert "/api/users/me" in paths
    assert "/api/items" in paths
    assert "/api/items/{item_id}" in paths
    assert "/api/stats/items" in paths
