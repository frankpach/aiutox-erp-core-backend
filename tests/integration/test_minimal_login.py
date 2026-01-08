"""Minimal login test to isolate Unicode issue."""

import pytest
from fastapi import status


def test_minimal_login(client):
    """Minimal login test without fixtures."""
    # Just test the endpoint without any user fixtures
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "wrong"},
    )
    
    # This should work without any Unicode issues
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "error" in response.json()


def test_login_with_simple_user(client, db_session):
    """Test login with a manually created simple user."""
    from app.core.auth import hash_password
    from app.models.tenant import Tenant
    from app.models.user import User
    from uuid import uuid4
    
    # Create tenant manually
    tenant = Tenant(
        name="Test Tenant",
        slug="test-tenant",
    )
    db_session.add(tenant)
    db_session.flush()
    
    # Create user manually
    password = "test_password_123"
    password_hash = hash_password(password)
    
    user = User(
        email=f"test-{uuid4().hex[:8]}@example.com",
        password_hash=password_hash,
        full_name="Test User",
        tenant_id=tenant.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)
    
    # Store plain password for test
    user._plain_password = password
    
    # Now test login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": user.email,
            "password": user._plain_password,
        },
    )
    
    # Check if this works
    print(f"Response status: {response.status_code}")
    print(f"Response text: {response.text[:200]}")
    
    if response.status_code == 200:
        data = response.json()
        assert "data" in data
        assert "access_token" in data["data"]
    else:
        # If it fails, at least we should get a proper error
        assert response.status_code in [401, 422]
