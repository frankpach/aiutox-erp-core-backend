"""Integration tests for /me endpoint."""

import time
from datetime import timedelta

import pytest
from fastapi import status

from app.core.auth import create_access_token
from app.services.auth_service import AuthService


def test_get_me_authenticated(client, db_session, test_user):
    """Test that authenticated user can get their information."""
    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(test_user)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["email"] == test_user.email
    assert data["tenant_id"] == str(test_user.tenant_id)
    assert data["full_name"] == test_user.full_name


def test_get_me_includes_roles_and_permissions(client, db_session, test_user_with_roles):
    """Test that /me response includes roles and permissions."""
    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(test_user_with_roles)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "roles" in data
    assert "permissions" in data
    assert isinstance(data["roles"], list)
    assert isinstance(data["permissions"], list)
    # User should have admin role
    assert "admin" in data["roles"]


def test_get_me_invalid_token(client):
    """Test that /me endpoint returns 401 for invalid token."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token_string"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "detail" in data
    assert "error" in data["detail"]
    assert data["detail"]["error"]["code"] == "AUTH_INVALID_TOKEN"


def test_get_me_expired_token(client, test_user):
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

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "detail" in data
    assert "error" in data["detail"]


def test_get_me_inactive_user(client, db_session, test_user_inactive):
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
    response = client.get(
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


def test_get_me_wrong_token_type(client, db_session, test_user):
    """Test that /me endpoint returns 401 for refresh token (wrong type)."""
    from app.core.auth import create_refresh_token

    refresh_token = create_refresh_token(test_user.id)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "detail" in data
    assert "error" in data["detail"]
    assert data["detail"]["error"]["code"] == "AUTH_INVALID_TOKEN"



