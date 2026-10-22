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
    updated = {**sample_item_data, "name": f"updated_{item_id}", "price": "99.00"}
    response = client.put(f"/api/items/{item_id}", json=updated, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == f"updated_{item_id}"
    assert response.json()["price"] == "99.00"

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
            json={**sample_item_data, "name": f"{sample_item_data['name']}_page_{i}"},
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


def test_price_is_exact_decimal(client: TestClient, auth_headers, sample_item_data):
    """Money is NUMERIC/Decimal: no float rounding, serialized as a string."""
    response = client.post(
        "/api/items", json={**sample_item_data, "price": "0.10"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["price"] == "0.10"


def test_price_rejects_sub_cent_values(client: TestClient, auth_headers, sample_item_data):
    """More than 2 decimal places is a validation error, not silent rounding."""
    response = client.post(
        "/api/items", json={**sample_item_data, "price": "1.005"}, headers=auth_headers
    )
    assert response.status_code == 422


def test_duplicate_name_conflict(client: TestClient, auth_headers, sample_item_data):
    """The unique constraint lives in the DB; violations become 409 Conflict."""
    assert client.post("/api/items", json=sample_item_data, headers=auth_headers).status_code == 200

    response = client.post("/api/items", json=sample_item_data, headers=auth_headers)
    assert response.status_code == 409
    # No SQL / constraint internals leak to the client
    assert response.json() == {"detail": "The request conflicts with existing data."}


def test_update_to_duplicate_name_conflict(
    client: TestClient, auth_headers, sample_item_data
):
    """Renaming onto an existing name is also a 409 (not CrudRouter's raw 422)."""
    first = client.post("/api/items", json=sample_item_data, headers=auth_headers).json()
    other = {**sample_item_data, "name": sample_item_data["name"] + "_other"}
    second = client.post("/api/items", json=other, headers=auth_headers).json()

    response = client.put(
        f"/api/items/{second['id']}",
        json={**other, "name": first["name"]},
        headers=auth_headers,
    )
    assert response.status_code == 409
    # The failed update was rolled back
    assert client.get(f"/api/items/{second['id']}").json()["name"] == other["name"]


def test_db_check_constraint(client: TestClient):
    """The DB rejects a negative price even when the API schema is bypassed."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    from app.core.database import SessionLocal
    from app.models.item import Item as ItemModel

    with SessionLocal() as db:
        db.add(ItemModel(name=f"negative_{uuid.uuid4().hex[:8]}", price=-1))
        with pytest.raises(IntegrityError):
            db.commit()
