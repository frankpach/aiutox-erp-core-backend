"""Test client without database fixture."""

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app


def test_client_without_db():
    """Test client without database fixture."""

    # Create client directly without any database overrides
    with TestClient(app) as client:
        # Test login without any database setup
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrong"},
        )

        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text[:200]}")

        # This should work without any Unicode issues
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "error" in response.json()
