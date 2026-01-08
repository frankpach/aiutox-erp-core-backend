"""Fixed login test that bypasses the problematic database session fixture."""

import pytest
from fastapi import status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.auth import hash_password
from app.models.tenant import Tenant
from app.models.user import User
from app.core.db.deps import get_db
from fastapi.testclient import TestClient
from app.main import app
from uuid import uuid4
from pathlib import Path
from dotenv import load_dotenv


@pytest.fixture(scope="function")
def simple_client():
    """Create a test client without database session fixture."""
    
    # Load environment variables
    backend_dir = Path(__file__).parent.parent
    env_files = [
        backend_dir / ".env",
        backend_dir.parent / ".env",
    ]
    
    for env_file in env_files:
        if env_file.exists():
            load_dotenv(env_file)
    
    # Create direct database connection
    import os
    from app.core.config_file import get_settings
    
    settings = get_settings()
    database_url = settings.database_url
    
    # Convert to test database URL
    if "db:" in database_url or "@db:" in database_url:
        test_db_url = database_url.replace("@db:5432", "@localhost:15432")
        test_db_url = test_db_url.replace("db:5432", "localhost:15432")
        test_db_url = test_db_url.replace("@db/", "@localhost:15432/")
        test_db_url = test_db_url.replace("db/", "localhost:15432/")
    elif settings.POSTGRES_HOST == "db" and settings.POSTGRES_PORT == 5432:
        test_db_url = (
            f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
            f"@localhost:15432/{settings.POSTGRES_DB}"
        )
    else:
        if settings.POSTGRES_HOST == "db":
            test_db_url = (
                f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
                f"@localhost:15432/{settings.POSTGRES_DB}"
            )
        else:
            test_db_url = database_url
    
    # Use test database name
    test_db_name = os.getenv("TEST_POSTGRES_DB", "aiutox_erp_test")
    if "/" in test_db_url:
        base_url = test_db_url.rsplit("/", 1)[0]
        database_url = f"{base_url}/{test_db_name}"
    else:
        database_url = test_db_url.replace("/aiutox_erp_dev", f"/{test_db_name}")
        database_url = database_url.replace("/postgres", f"/{test_db_name}")
    
    # Create engine and session
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": 5,
            "options": "-c timezone=utc"
        }
    )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
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
        except:
            pass
        try:
            db.close()
        except:
            pass
        
        # Clear dependency override
        app.dependency_overrides.clear()


def test_login_success_fixed(simple_client):
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
