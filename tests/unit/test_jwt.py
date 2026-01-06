"""Unit tests for JWT token creation and validation utilities."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from app.core.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_refresh_token,
)
from app.core.config_file import get_settings

settings = get_settings()


def test_create_access_token():
    """Test that create_access_token creates a valid token."""
    data = {
        "sub": str(uuid4()),
        "tenant_id": str(uuid4()),
        "roles": ["admin"],
        "permissions": ["auth.manage_users"],
    }
    token = create_access_token(data)

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_token_valid():
    """Test that decode_token decodes a valid token."""
    user_id = uuid4()
    tenant_id = uuid4()
    data = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "roles": ["admin"],
        "permissions": ["auth.manage_users"],
    }
    token = create_access_token(data)
    decoded = decode_token(token)

    assert decoded is not None
    assert decoded["sub"] == str(user_id)
    assert decoded["tenant_id"] == str(tenant_id)
    assert decoded["roles"] == ["admin"]
    assert decoded["permissions"] == ["auth.manage_users"]
    assert decoded["type"] == "access"
    assert "exp" in decoded
    assert "iat" in decoded


def test_decode_token_expired():
    """Test that decode_token returns None for expired token."""
    data = {
        "sub": str(uuid4()),
        "tenant_id": str(uuid4()),
    }
    # Create token with very short expiration (1 second ago)
    expires_delta = timedelta(seconds=-1)
    token = create_access_token(data, expires_delta=expires_delta)

    # Wait a bit to ensure expiration
    import time
    time.sleep(2)

    decoded = decode_token(token)
    assert decoded is None


def test_create_refresh_token():
    """Test that create_refresh_token creates a valid refresh token."""
    user_id = uuid4()
    token = create_refresh_token(user_id)

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_verify_refresh_token_valid():
    """Test that verify_refresh_token validates a valid refresh token."""
    user_id = uuid4()
    token = create_refresh_token(user_id)
    payload = verify_refresh_token(token)

    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"
    assert "exp" in payload
    assert "iat" in payload


def test_verify_refresh_token_invalid_type():
    """Test that verify_refresh_token rejects access tokens."""
    data = {
        "sub": str(uuid4()),
        "tenant_id": str(uuid4()),
    }
    # Create access token
    access_token = create_access_token(data)

    # Try to verify as refresh token (should fail)
    payload = verify_refresh_token(access_token)
    assert payload is None


def test_verify_refresh_token_invalid_signature():
    """Test that verify_refresh_token rejects tokens with invalid signature."""
    user_id = uuid4()
    token = create_refresh_token(user_id)

    # Modify token (invalid signature)
    invalid_token = token[:-5] + "xxxxx"

    payload = verify_refresh_token(invalid_token)
    assert payload is None


def test_token_payload_contains_required_fields():
    """Test that access token payload contains all required fields."""
    user_id = uuid4()
    tenant_id = uuid4()
    roles = ["admin", "manager"]
    permissions = ["auth.manage_users", "system.configure"]

    data = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "roles": roles,
        "permissions": permissions,
    }
    token = create_access_token(data)
    decoded = decode_token(token)

    assert decoded is not None
    assert "sub" in decoded
    assert "tenant_id" in decoded
    assert "roles" in decoded
    assert "permissions" in decoded
    assert "exp" in decoded
    assert "iat" in decoded
    assert "type" in decoded

    assert decoded["sub"] == str(user_id)
    assert decoded["tenant_id"] == str(tenant_id)
    assert decoded["roles"] == roles
    assert decoded["permissions"] == permissions
    assert decoded["type"] == "access"


def test_decode_token_invalid():
    """Test that decode_token returns None for invalid token."""
    invalid_token = "invalid.token.string"
    decoded = decode_token(invalid_token)
    assert decoded is None


def test_create_access_token_with_custom_expiration():
    """Test that create_access_token accepts custom expiration."""
    data = {"sub": str(uuid4())}
    expires_delta = timedelta(minutes=30)
    token = create_access_token(data, expires_delta=expires_delta)

    decoded = decode_token(token)
    assert decoded is not None

    # Verify expiration is approximately 30 minutes from now
    exp_timestamp = decoded["exp"]
    iat_timestamp = decoded["iat"]
    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    iat_datetime = datetime.fromtimestamp(iat_timestamp, tz=timezone.utc)

    diff = exp_datetime - iat_datetime
    assert abs(diff.total_seconds() - 30 * 60) < 5  # Allow 5 seconds tolerance


def test_refresh_token_expiration():
    """Test that refresh token has correct expiration (7 days)."""
    user_id = uuid4()
    token = create_refresh_token(user_id)
    payload = verify_refresh_token(token)

    assert payload is not None
    exp_timestamp = payload["exp"]
    iat_timestamp = payload["iat"]
    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    iat_datetime = datetime.fromtimestamp(iat_timestamp, tz=timezone.utc)

    diff = exp_datetime - iat_datetime
    expected_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
    assert abs(diff.days - expected_days) < 1  # Allow 1 day tolerance


def test_refresh_token_with_remember_me_true():
    """Test that refresh token with remember_me=True expires in 30 days."""
    user_id = uuid4()
    token = create_refresh_token(user_id, remember_me=True)
    payload = verify_refresh_token(token)

    assert payload is not None
    exp_timestamp = payload["exp"]
    iat_timestamp = payload["iat"]
    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    iat_datetime = datetime.fromtimestamp(iat_timestamp, tz=timezone.utc)

    diff = exp_datetime - iat_datetime
    expected_days = settings.REFRESH_TOKEN_REMEMBER_ME_DAYS
    assert abs(diff.days - expected_days) < 1  # Allow 1 day tolerance


def test_refresh_token_with_remember_me_false():
    """Test that refresh token with remember_me=False expires in 7 days."""
    user_id = uuid4()
    token = create_refresh_token(user_id, remember_me=False)
    payload = verify_refresh_token(token)

    assert payload is not None
    exp_timestamp = payload["exp"]
    iat_timestamp = payload["iat"]
    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    iat_datetime = datetime.fromtimestamp(iat_timestamp, tz=timezone.utc)

    diff = exp_datetime - iat_datetime
    expected_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
    assert abs(diff.days - expected_days) < 1  # Allow 1 day tolerance


def test_access_token_expires_in_60_minutes():
    """Test that access token expires in 60 minutes."""
    data = {
        "sub": str(uuid4()),
        "tenant_id": str(uuid4()),
        "roles": ["admin"],
        "permissions": ["auth.manage_users"],
    }
    token = create_access_token(data)
    decoded = decode_token(token)

    assert decoded is not None
    exp_timestamp = decoded["exp"]
    iat_timestamp = decoded["iat"]
    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    iat_datetime = datetime.fromtimestamp(iat_timestamp, tz=timezone.utc)

    diff = exp_datetime - iat_datetime
    expected_minutes = 60  # Hardcoded expected value for this specific test
    assert abs(diff.total_seconds() / 60 - expected_minutes) < 1  # Allow 1 minute tolerance



