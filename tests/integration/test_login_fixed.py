"""Fixed login test that bypasses the problematic database session fixture."""

from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.auth import hash_password
from app.core.db.deps import get_db
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User


@pytest.fixture(scope="function")
def simple_client():
    """Create a test client without database session fixture."""

    # Import the test database URL from conftest
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from conftest import TEST_DATABASE_URL

    # Use the same database URL as conftest.py
    database_url = TEST_DATABASE_URL

    # Create engine and run migrations first
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5, "options": "-c timezone=utc"},
    )

    # Run migrations to ensure tables exist
    from app.core.migrations.manager import MigrationManager

    try:
        manager = MigrationManager()
        manager.engine = engine
        manager.alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        result = manager.apply_migrations()

        if not result.success:
            print(f"Migration failed: {result.errors}")
            raise RuntimeError(f"Failed to setup database: {result.errors}")

        print("Migrations applied successfully")
    except Exception as e:
        print(f"Error running migrations: {e}")
        raise

    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()

    # Create test data
    tenant = Tenant(
        name="Test Tenant",
        slug=f"test-tenant-{uuid4().hex[:8]}",
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    password = "test_password_123"
    password_hash = hash_password(password)

    user = User(
        email=f"test-{uuid4().hex[:8]}@example.com",
        password_hash=password_hash,
        full_name="Test User",
        tenant_id=tenant.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Store plain password for test
    user._plain_password = password

    # Override get_db with our session
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client, user
    finally:
        # Clean up
        try:
            db.query(User).filter(User.id == user.id).delete()
            db.query(Tenant).filter(Tenant.id == tenant.id).delete()
            db.commit()
        except Exception:
            pass
        try:
            db.close()
        except Exception:
            pass

        # Clear dependency override
        app.dependency_overrides.clear()


def test_login_success_fixed(simple_client, setup_database):
    """Test login endpoint with fixed client that bypasses problematic fixture."""
    client, test_user = simple_client

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
    from app.core.auth.jwt import decode_token

    decoded = decode_token(token_data["access_token"])
    assert decoded is not None
    assert decoded["sub"] == str(test_user.id)
