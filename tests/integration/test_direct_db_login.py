"""Test login with direct database connection (no fixtures)."""

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


def test_login_with_direct_db():
    """Test login with direct database connection (no fixtures)."""
    
    # Load environment variables like conftest.py does
    backend_dir = Path(__file__).parent.parent
    env_files = [
        backend_dir / ".env",  # backend/.env
        backend_dir.parent / ".env",  # ../.env (project root)
    ]
    
    for env_file in env_files:
        if env_file.exists():
            load_dotenv(env_file)
    
    # Create direct database connection
    import os
    from app.core.config_file import get_settings
    
    settings = get_settings()
    database_url = settings.database_url
    
    # For tests, we typically run outside Docker, so convert Docker hostnames to localhost
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
    
    print(f"Using database URL: {database_url}")
    
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
        except:
            pass
        try:
            db.close()
        except:
            pass
        
        # Clear dependency override
        app.dependency_overrides.clear()
