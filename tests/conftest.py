"""
Test configuration and fixtures.

This module contains pytest configuration and common fixtures
used across all test modules.
"""

import os
import tempfile
import uuid

# Configure the app for tests *before* importing it
_db_dir = tempfile.mkdtemp(prefix="fastapi-v3-test-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_dir}/test.db"
os.environ["REDIS_URL"] = ""
os.environ["AUTH_RATE_LIMIT_TIMES"] = "1000"
os.environ["RATE_LIMIT_TIMES"] = "1000"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    """Create a test client (runs the lifespan: DB tables + cache init)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    unique_id = str(uuid.uuid4())[:8]
    return {
        "email": f"test_{unique_id}@example.com",
        "password": "testpassword123",
        "full_name": "Test User",
    }


@pytest.fixture
def auth_headers(client: TestClient, sample_user_data):
    """Register a new user, log in and return the Authorization header."""
    response = client.post("/api/auth/register", json=sample_user_data)
    assert response.status_code == 201

    response = client.post(
        "/api/auth/jwt/login",
        data={
            "username": sample_user_data["email"],
            "password": sample_user_data["password"],
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_item_data():
    """Sample item data for testing."""
    return {
        "name": f"item_{uuid.uuid4().hex[:8]}",
        "description": "test",
        "price": "10.50",
    }
