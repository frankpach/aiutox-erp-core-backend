"""Integration tests for /me endpoint."""

import time
from datetime import timedelta

from fastapi import status

from app.core.auth import create_access_token
from app.services.auth_service import AuthService


def test_get_me_authenticated(client_with_db, db_session, test_user):
    """Test that authenticated user can get their information."""
    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(test_user)

    response = client_with_db.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # Verify StandardResponse structure
    assert "data" in data
    user_data = data["data"]
    assert user_data["id"] == str(test_user.id)
    assert user_data["email"] == test_user.email
    assert user_data["tenant_id"] == str(test_user.tenant_id)
    assert user_data["full_name"] == test_user.full_name


def test_get_me_includes_roles_and_permissions(client_with_db, db_session, test_user_with_roles):
    """Test that /me response includes roles and permissions."""
    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(test_user_with_roles)

    response = client_with_db.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # Verify StandardResponse structure
    assert "data" in data
    user_data = data["data"]
    assert "roles" in user_data
    assert "permissions" in user_data
    assert isinstance(user_data["roles"], list)
    assert isinstance(user_data["permissions"], list)
    # User should have admin role
    assert "admin" in user_data["roles"]


def test_get_me_invalid_token(client):
    """Test that /me endpoint returns 401 for invalid token."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token_string"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AUTH_INVALID_TOKEN"


def test_get_me_expired_token(client_with_db, test_user):
    """Test that /me endpoint returns 401 for expired token."""
    # Create expired token
    token_data = {
        "sub": str(test_user.id),
        "tenant_id": str(test_user.tenant_id),
        "roles": [],
        "permissions": [],
    }
    expired_token = create_access_token(token_data, expires_delta=timedelta(seconds=-1))

    # Wait to ensure expiration
    time.sleep(2)

    response = client_with_db.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AUTH_INVALID_TOKEN"


def test_get_me_inactive_user(client_with_db, db_session, test_user_inactive):
    """Test that inactive user cannot access /me endpoint."""
    # First, we need to create a token for inactive user
    # But get_current_user should reject inactive users
    token_data = {
        "sub": str(test_user_inactive.id),
        "tenant_id": str(test_user_inactive.tenant_id),
        "roles": [],
        "permissions": [],
    }
    access_token = create_access_token(token_data)

    # Try to access /me
    response = client_with_db.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # Should be rejected (403 Forbidden for inactive user)
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


def test_get_me_missing_authorization_header(client):
    """Test that /me endpoint returns 401 when Authorization header is missing."""
    response = client.get("/api/v1/auth/me")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_me_malformed_authorization_header(client):
    """Test that /me endpoint returns 401 for malformed Authorization header."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "InvalidFormat token"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_me_wrong_token_type(client_with_db, db_session, test_user):
    """Test that /me endpoint returns 401 for refresh token (wrong type)."""
    from app.core.auth import create_refresh_token

    refresh_token = create_refresh_token(test_user.id)

    response = client_with_db.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AUTH_INVALID_TOKEN"



