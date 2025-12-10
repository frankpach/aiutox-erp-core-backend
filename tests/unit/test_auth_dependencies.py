"""Unit tests for authentication dependencies."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status

from app.core.auth.dependencies import (
    get_current_user,
    get_user_permissions,
    verify_tenant_access,
)
from app.models.tenant import Tenant
from app.models.user import User


@pytest.mark.asyncio
async def test_get_current_user_valid_token(db_session, test_user):
    """Test that get_current_user returns user for valid token."""
    # Create valid access token
    token_data = {
        "sub": str(test_user.id),
        "tenant_id": str(test_user.tenant_id),
        "roles": [],
        "permissions": [],
        "type": "access",
    }
    from app.core.auth import create_access_token

    token = create_access_token(token_data)

    # Mock oauth2_scheme dependency
    with patch("app.core.auth.dependencies.oauth2_scheme") as mock_oauth:
        mock_oauth.return_value = token

        # Call get_current_user
        result = await get_current_user(token, db_session)

        assert result is not None
        assert result.id == test_user.id
        assert result.email == test_user.email
        assert result.tenant_id == test_user.tenant_id


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(db_session):
    """Test that get_current_user raises exception for invalid token."""
    invalid_token = "invalid.token.string"

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(invalid_token, db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail["error"]["code"] == "AUTH_INVALID_TOKEN"
    assert exc_info.value.detail["error"]["message"] == "Invalid or expired token"


@pytest.mark.asyncio
async def test_get_current_user_expired_token(db_session, test_user):
    """Test that get_current_user raises exception for expired token."""
    from datetime import timedelta

    token_data = {
        "sub": str(test_user.id),
        "tenant_id": str(test_user.tenant_id),
        "roles": [],
        "permissions": [],
        "type": "access",
    }
    from app.core.auth import create_access_token

    # Create expired token
    expired_token = create_access_token(token_data, expires_delta=timedelta(seconds=-1))

    # Wait to ensure expiration
    import time

    time.sleep(2)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(expired_token, db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail["error"]["code"] == "AUTH_INVALID_TOKEN"


@pytest.mark.asyncio
async def test_get_current_user_wrong_token_type(db_session, test_user):
    """Test that get_current_user raises exception for refresh token (wrong type)."""
    from app.core.auth import create_refresh_token

    refresh_token = create_refresh_token(test_user.id)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(refresh_token, db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail["error"]["code"] == "AUTH_INVALID_TOKEN"
    assert exc_info.value.detail["error"]["message"] == "Invalid token type"


@pytest.mark.asyncio
async def test_get_current_user_missing_user_id(db_session):
    """Test that get_current_user raises exception when token lacks user_id."""
    token_data = {
        "tenant_id": str(uuid4()),
        "roles": [],
        "permissions": [],
        "type": "access",
        # Missing "sub"
    }
    from app.core.auth import create_access_token

    token = create_access_token(token_data)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token, db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail["error"]["code"] == "AUTH_INVALID_TOKEN"
    assert exc_info.value.detail["error"]["message"] == "Token missing user ID"


@pytest.mark.asyncio
async def test_get_current_user_invalid_user_id_format(db_session):
    """Test that get_current_user raises exception for invalid user_id format."""
    token_data = {
        "sub": "not-a-valid-uuid",
        "tenant_id": str(uuid4()),
        "roles": [],
        "permissions": [],
        "type": "access",
    }
    from app.core.auth import create_access_token

    token = create_access_token(token_data)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token, db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail["error"]["code"] == "AUTH_INVALID_TOKEN"
    assert exc_info.value.detail["error"]["message"] == "Invalid user ID in token"


@pytest.mark.asyncio
async def test_get_current_user_missing_tenant_id(db_session, test_user):
    """Test that get_current_user raises exception when token lacks tenant_id."""
    token_data = {
        "sub": str(test_user.id),
        "roles": [],
        "permissions": [],
        "type": "access",
        # Missing "tenant_id"
    }
    from app.core.auth import create_access_token

    token = create_access_token(token_data)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token, db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail["error"]["code"] == "AUTH_INVALID_TOKEN"
    assert exc_info.value.detail["error"]["message"] == "Token missing tenant ID"


@pytest.mark.asyncio
async def test_get_current_user_invalid_tenant_id_format(db_session, test_user):
    """Test that get_current_user raises exception for invalid tenant_id format."""
    token_data = {
        "sub": str(test_user.id),
        "tenant_id": "not-a-valid-uuid",
        "roles": [],
        "permissions": [],
        "type": "access",
    }
    from app.core.auth import create_access_token

    token = create_access_token(token_data)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token, db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail["error"]["code"] == "AUTH_INVALID_TOKEN"
    assert exc_info.value.detail["error"]["message"] == "Invalid tenant ID in token"


@pytest.mark.asyncio
async def test_get_current_user_not_found(db_session, test_tenant):
    """Test that get_current_user raises exception when user doesn't exist."""
    non_existent_user_id = uuid4()
    token_data = {
        "sub": str(non_existent_user_id),
        "tenant_id": str(test_tenant.id),
        "roles": [],
        "permissions": [],
        "type": "access",
    }
    from app.core.auth import create_access_token

    token = create_access_token(token_data)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token, db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail["error"]["code"] == "AUTH_USER_NOT_FOUND"
    assert exc_info.value.detail["error"]["message"] == "User not found"


@pytest.mark.asyncio
async def test_get_current_user_tenant_mismatch(db_session, test_user, test_tenant):
    """Test that get_current_user raises exception when tenant_id doesn't match."""
    # Create another tenant
    other_tenant = Tenant(
        name="Other Tenant",
        slug=f"other-tenant-{uuid4().hex[:8]}",
    )
    db_session.add(other_tenant)
    db_session.commit()
    db_session.refresh(other_tenant)

    # Create token with different tenant_id
    token_data = {
        "sub": str(test_user.id),
        "tenant_id": str(other_tenant.id),  # Different tenant
        "roles": [],
        "permissions": [],
        "type": "access",
    }
    from app.core.auth import create_access_token

    token = create_access_token(token_data)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token, db_session)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail["error"]["code"] == "AUTH_TENANT_MISMATCH"
    assert exc_info.value.detail["error"]["message"] == "Token tenant does not match user tenant"


@pytest.mark.asyncio
async def test_get_current_user_inactive(db_session, test_user_inactive):
    """Test that get_current_user raises exception for inactive user."""
    token_data = {
        "sub": str(test_user_inactive.id),
        "tenant_id": str(test_user_inactive.tenant_id),
        "roles": [],
        "permissions": [],
        "type": "access",
    }
    from app.core.auth import create_access_token

    token = create_access_token(token_data)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token, db_session)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail["error"]["code"] == "AUTH_USER_INACTIVE"
    assert exc_info.value.detail["error"]["message"] == "User account is inactive"


@pytest.mark.asyncio
async def test_get_user_permissions_returns_empty_set(db_session, test_user):
    """Test that get_user_permissions returns empty set in Phase 1."""
    # Create valid token and get user
    token_data = {
        "sub": str(test_user.id),
        "tenant_id": str(test_user.tenant_id),
        "roles": [],
        "permissions": [],
        "type": "access",
    }
    from app.core.auth import create_access_token

    token = create_access_token(token_data)
    current_user = await get_current_user(token, db_session)

    # Get permissions
    permissions = await get_user_permissions(current_user, db_session)

    # Phase 1: Should return empty set
    assert isinstance(permissions, set)
    assert len(permissions) == 0


def test_verify_tenant_access_valid(db_session, test_user, test_tenant):
    """Test that verify_tenant_access returns True for matching tenant."""
    result = verify_tenant_access(test_user, test_tenant.id)
    assert result is True


def test_verify_tenant_access_invalid(db_session, test_user):
    """Test that verify_tenant_access returns False for different tenant."""
    other_tenant_id = uuid4()
    result = verify_tenant_access(test_user, other_tenant_id)
    assert result is False

