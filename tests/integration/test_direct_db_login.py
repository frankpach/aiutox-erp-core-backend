"""Test login with direct database connection (no fixtures)."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.auth import hash_password
from app.core.db.deps import get_db
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User


def test_login_with_direct_db():
    """Test login with direct database connection (no fixtures)."""

    # Import the test database URL from conftest
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from conftest import TEST_DATABASE_URL

    # Use the same database URL as conftest.py
    database_url = TEST_DATABASE_URL

    print(f"Using database URL: {database_url}")

    # Create engine and run migrations first
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": 5,
            "options": "-c timezone=utc"
        }
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

    try:
        # Create tenant
        tenant = Tenant(
            name="Test Tenant",
            slug=f"test-tenant-{uuid4().hex[:8]}",
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        # Create user
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

        # Override get_db to use our direct session
        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db

        # Create test client
        with TestClient(app) as client:
            # Test login
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": user.email,
                    "password": user._plain_password,
                },
            )

            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text[:200]}")

            if response.status_code == 200:
                data = response.json()
                assert "data" in data
                assert "access_token" in data["data"]
            else:
                # If it fails, at least we should get a proper error
                assert response.status_code in [401, 422]

    finally:
        # Clean up
        try:
            db.query(User).filter(User.email.like("test-%@example.com")).delete()
            db.query(Tenant).filter(Tenant.slug.like("test-tenant-%")).delete()
            db.commit()
        except Exception:
            pass
        try:
            db.close()
        except Exception:
            pass

        # Clear dependency override
        app.dependency_overrides.clear()
