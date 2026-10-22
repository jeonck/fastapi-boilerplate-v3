"""
Test Authentication (FastAPI Users).

Registration, JWT login, current user and protected endpoints.
"""

from fastapi.testclient import TestClient


def test_register(client: TestClient, sample_user_data):
    """Test user registration."""
    response = client.post("/api/auth/register", json=sample_user_data)
    assert response.status_code == 201

    data = response.json()
    assert data["email"] == sample_user_data["email"]
    assert data["full_name"] == sample_user_data["full_name"]
    assert data["is_active"] is True
    assert data["is_superuser"] is False
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_duplicate_email(client: TestClient, sample_user_data):
    """Test that registering the same email twice fails."""
    client.post("/api/auth/register", json=sample_user_data)
    response = client.post("/api/auth/register", json=sample_user_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "REGISTER_USER_ALREADY_EXISTS"


def test_register_cannot_become_superuser(client: TestClient, sample_user_data):
    """Test that is_superuser is ignored on public registration."""
    response = client.post(
        "/api/auth/register", json={**sample_user_data, "is_superuser": True}
    )
    assert response.status_code == 201
    assert response.json()["is_superuser"] is False


def test_login_bad_credentials(client: TestClient, sample_user_data):
    """Test login with a wrong password."""
    client.post("/api/auth/register", json=sample_user_data)
    response = client.post(
        "/api/auth/jwt/login",
        data={"username": sample_user_data["email"], "password": "wrong-password"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "LOGIN_BAD_CREDENTIALS"


def test_current_user(client: TestClient, auth_headers, sample_user_data):
    """Test fetching the current user with a JWT."""
    response = client.get("/api/users/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == sample_user_data["email"]


def test_update_current_user(client: TestClient, auth_headers):
    """Test updating the current user's profile."""
    response = client.patch(
        "/api/users/me", headers=auth_headers, json={"full_name": "Updated Name"}
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Name"


def test_current_user_requires_auth(client: TestClient):
    """Test that /users/me requires authentication."""
    response = client.get("/api/users/me")
    assert response.status_code == 401


def test_invalid_token(client: TestClient):
    """Test that an invalid token is rejected."""
    response = client.get(
        "/api/users/me", headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401


def test_protected_demo(client: TestClient, auth_headers, sample_user_data):
    """Test the protected demo endpoint."""
    assert client.get("/api/demo/protected").status_code == 401

    response = client.get("/api/demo/protected", headers=auth_headers)
    assert response.status_code == 200
    assert sample_user_data["email"] in response.json()["message"]
