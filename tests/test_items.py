"""
Test Items CRUD (FastAPI-CrudRouter).

The Item endpoints are generated automatically by CrudRouter.
"""

import asyncio
import uuid

from fastapi.testclient import TestClient

from app.scripts.create_superuser import create_superuser


def _superuser_headers(client: TestClient) -> dict:
    email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    password = "adminpassword123"
    asyncio.run(create_superuser(email, password))
    response = client.post(
        "/api/auth/jwt/login", data={"username": email, "password": password}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_create_item_requires_auth(client: TestClient, sample_item_data):
    """Test that creating an item requires login."""
    response = client.post("/api/items", json=sample_item_data)
    assert response.status_code == 401


def test_item_crud_flow(client: TestClient, auth_headers, sample_item_data):
    """Test the full create -> read -> update -> delete flow."""
    # Create
    response = client.post("/api/items", json=sample_item_data, headers=auth_headers)
    assert response.status_code == 200
    item = response.json()
    assert item["name"] == sample_item_data["name"]
    assert item["price"] == sample_item_data["price"]
    item_id = item["id"]

    # Read one (public)
    response = client.get(f"/api/items/{item_id}")
    assert response.status_code == 200
    assert response.json()["name"] == sample_item_data["name"]

    # Read all (public)
    response = client.get("/api/items")
    assert response.status_code == 200
    assert any(i["id"] == item_id for i in response.json())

    # Update
    updated = {**sample_item_data, "name": "updated", "price": 99.0}
    response = client.put(f"/api/items/{item_id}", json=updated, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "updated"
    assert response.json()["price"] == 99.0

    # Delete
    response = client.delete(f"/api/items/{item_id}", headers=auth_headers)
    assert response.status_code == 200
    assert client.get(f"/api/items/{item_id}").status_code == 404


def test_item_validation(client: TestClient, auth_headers):
    """Test that invalid payloads are rejected."""
    response = client.post(
        "/api/items", json={"name": "", "price": -1}, headers=auth_headers
    )
    assert response.status_code == 422


def test_item_pagination(client: TestClient, auth_headers, sample_item_data):
    """Test skip/limit pagination."""
    for i in range(3):
        client.post(
            "/api/items",
            json={**sample_item_data, "name": f"page_{i}"},
            headers=auth_headers,
        )
    response = client.get("/api/items", params={"limit": 2})
    assert response.status_code == 200
    assert len(response.json()) == 2

    response = client.get("/api/items", params={"limit": 1000})
    assert response.status_code == 422


def test_get_missing_item(client: TestClient):
    """Test reading a non-existent item."""
    response = client.get("/api/items/999999")
    assert response.status_code == 404


def test_delete_all_requires_superuser(client: TestClient, auth_headers):
    """Test that deleting all items is restricted to superusers."""
    response = client.delete("/api/items", headers=auth_headers)
    assert response.status_code == 403

    response = client.delete("/api/items", headers=_superuser_headers(client))
    assert response.status_code == 200
    assert client.get("/api/items").json() == []
