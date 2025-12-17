"""Integration tests for authentication endpoints."""

import pytest
from fastapi import status

from app.core.auth import create_access_token, decode_token
from app.services.auth_service import AuthService


def test_login_success(client, test_user):
    """Test that login endpoint returns both tokens on success."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": test_user._plain_password,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # Verify StandardResponse structure
    assert "data" in data
    assert "meta" in data
    assert "error" in data
    assert data["meta"] is None
    assert data["error"] is None

    # Verify token data
    token_data = data["data"]
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert "token_type" in token_data
    assert token_data["token_type"] == "bearer"

    # Verify access token is valid
    decoded = decode_token(token_data["access_token"])
    assert decoded is not None
    assert decoded["sub"] == str(test_user.id)


def test_login_invalid_credentials(client, test_user):
    """Test that login endpoint returns generic error for invalid credentials."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "wrong_password",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
    assert data["error"]["message"] == "Invalid credentials"


def test_login_user_not_exists(client):
    """Test that login endpoint returns same error for non-existent user (doesn't reveal existence)."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "any_password",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
    assert data["error"]["message"] == "Invalid credentials"
    # Should not reveal that user doesn't exist


def test_refresh_token_success(client, db_session, test_user):
    """Test that refresh token endpoint generates new access token."""
    auth_service = AuthService(db_session)
    refresh_token = auth_service.create_refresh_token_for_user(test_user)

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # Verify StandardResponse structure
    assert "data" in data
    assert "meta" in data
    assert "error" in data
    assert data["meta"] is None
    assert data["error"] is None

    # Verify token data
    token_data = data["data"]
    assert "access_token" in token_data
    assert "token_type" in token_data
    assert token_data["token_type"] == "bearer"

    # Verify new access token is valid
    decoded = decode_token(token_data["access_token"])
    assert decoded is not None
    assert decoded["sub"] == str(test_user.id)
    assert decoded["type"] == "access"


def test_refresh_token_invalid(client):
    """Test that refresh token endpoint returns error for invalid token."""
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_token"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AUTH_REFRESH_TOKEN_INVALID"


def test_logout_success(client, db_session, test_user):
    """Test that logout endpoint revokes refresh token."""
    auth_service = AuthService(db_session)
    refresh_token = auth_service.create_refresh_token_for_user(test_user)

    # Get access token for authentication
    token_data = {
        "sub": str(test_user.id),
        "tenant_id": str(test_user.tenant_id),
        "roles": [],
        "permissions": [],
    }
    access_token = create_access_token(token_data)

    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert data["data"]["message"] == "Logged out successfully"

    # Verify token is revoked
    new_token = auth_service.refresh_access_token(refresh_token)
    assert new_token is None


def test_get_me_success(client, db_session, test_user):
    """Test that GET /me endpoint returns user information."""
    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(test_user)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # Verify StandardResponse structure
    assert "data" in data
    assert "meta" in data
    assert "error" in data
    assert data["meta"] is None
    assert data["error"] is None

    # Verify user data
    user_data = data["data"]
    assert user_data["id"] == str(test_user.id)
    assert user_data["email"] == test_user.email
    assert user_data["tenant_id"] == str(test_user.tenant_id)
    assert "roles" in user_data
    assert "permissions" in user_data


def test_get_me_invalid_token(client):
    """Test that GET /me endpoint returns 401 for invalid token."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AUTH_INVALID_TOKEN"


def test_get_me_expired_token(client, test_user):
    """Test that GET /me endpoint returns 401 for expired token."""
    from datetime import timedelta

    # Create expired token
    token_data = {
        "sub": str(test_user.id),
        "tenant_id": str(test_user.tenant_id),
        "roles": [],
        "permissions": [],
    }
    expired_token = create_access_token(token_data, expires_delta=timedelta(seconds=-1))

    # Wait to ensure expiration
    import time
    time.sleep(2)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_me_no_token(client):
    """Test that GET /me endpoint returns 401 when no token is provided."""
    response = client.get("/api/v1/auth/me")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_refresh_token_revoked_after_creation(client, db_session, test_user):
    """Test that refresh token cannot be used after being revoked."""
    auth_service = AuthService(db_session)
    refresh_token = auth_service.create_refresh_token_for_user(test_user)

    # Revoke token
    auth_service.revoke_refresh_token(refresh_token, test_user.id)

    # Try to refresh with revoked token
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AUTH_REFRESH_TOKEN_INVALID"


def test_refresh_token_user_inactive_after_refresh(client, db_session, test_user):
    """Test that refresh fails if user becomes inactive after token creation."""
    auth_service = AuthService(db_session)
    refresh_token = auth_service.create_refresh_token_for_user(test_user)

    # Deactivate user
    test_user.is_active = False
    db_session.commit()

    # Try to refresh
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AUTH_REFRESH_TOKEN_INVALID"


def test_logout_invalid_refresh_token(client, db_session, test_user):
    """Test that logout returns error for invalid refresh token."""
    token_data = {
        "sub": str(test_user.id),
        "tenant_id": str(test_user.tenant_id),
        "roles": [],
        "permissions": [],
    }
    access_token = create_access_token(token_data)

    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "invalid_refresh_token"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AUTH_REFRESH_TOKEN_INVALID"


def test_logout_already_revoked_token(client, db_session, test_user):
    """Test that logout handles already revoked token gracefully."""
    auth_service = AuthService(db_session)
    refresh_token = auth_service.create_refresh_token_for_user(test_user)

    # Revoke token first
    auth_service.revoke_refresh_token(refresh_token, test_user.id)

    # Try to logout with already revoked token
    token_data = {
        "sub": str(test_user.id),
        "tenant_id": str(test_user.tenant_id),
        "roles": [],
        "permissions": [],
    }
    access_token = create_access_token(token_data)

    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AUTH_REFRESH_TOKEN_INVALID"


def test_login_response_format(client, test_user):
    """Test that login response follows API contract format."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": test_user._plain_password,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify StandardResponse structure
    assert "data" in data
    assert "meta" in data
    assert "error" in data
    assert data["meta"] is None
    assert data["error"] is None

    # Verify token data structure
    token_data = data["data"]
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert "token_type" in token_data
    assert token_data["token_type"] == "bearer"
    assert isinstance(token_data["access_token"], str)
    assert isinstance(token_data["refresh_token"], str)


def test_error_response_format(client):
    """Test that error responses follow API contract format."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "wrong_password",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()

    # Verify error response structure (API contract format: {"error": {...}, "data": null})
    assert "error" in data
    assert "data" in data
    assert data["data"] is None
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert "details" in data["error"]
    assert isinstance(data["error"]["code"], str)
    assert isinstance(data["error"]["message"], str)
    # details can be None or dict/string
    assert data["error"]["details"] is None or isinstance(data["error"]["details"], (dict, str))


def test_get_me_response_format(client, db_session, test_user):
    """Test that /me response follows API contract format."""
    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(test_user)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify StandardResponse structure
    assert "data" in data
    assert "meta" in data
    assert "error" in data
    assert data["meta"] is None
    assert data["error"] is None

    # Verify user data structure
    user_data = data["data"]
    assert "id" in user_data
    assert "email" in user_data
    assert "full_name" in user_data
    assert "tenant_id" in user_data
    assert "roles" in user_data
    assert "permissions" in user_data
    assert isinstance(user_data["roles"], list)
    assert isinstance(user_data["permissions"], list)


def test_multi_tenant_isolation(client, db_session, test_user, test_tenant):
    """Test that users cannot access resources from other tenants via token manipulation."""
    from uuid import uuid4

    from app.models.tenant import Tenant
    from app.models.user import User
    from app.core.auth import hash_password

    # Create another tenant
    other_tenant = Tenant(
        name="Other Tenant",
        slug=f"other-tenant-{uuid4().hex[:8]}",
    )
    db_session.add(other_tenant)
    db_session.commit()
    db_session.refresh(other_tenant)

    # Create user in other tenant
    other_user = User(
        email=f"other-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("password123"),
        full_name="Other User",
        tenant_id=other_tenant.id,
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    # Try to create token with test_user's ID but other_tenant's ID
    token_data = {
        "sub": str(test_user.id),  # test_user's ID
        "tenant_id": str(other_tenant.id),  # But other tenant's ID
        "roles": [],
        "permissions": [],
    }
    malicious_token = create_access_token(token_data)

    # Try to access /me with malicious token
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {malicious_token}"},
    )

    # Should be rejected due to tenant mismatch
    assert response.status_code == status.HTTP_403_FORBIDDEN
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AUTH_TENANT_MISMATCH"


def test_multi_tenant_valid_access(client, db_session, test_user):
    """Test that users can access their own tenant resources correctly."""
    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(test_user)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # Verify StandardResponse structure
    assert "data" in data
    # Verify tenant_id matches
    assert data["data"]["tenant_id"] == str(test_user.tenant_id)



