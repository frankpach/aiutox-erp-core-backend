#!/usr/bin/env python3
"""Debug script to test fixture creation."""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.auth import hash_password
from app.core.config_file import get_settings
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User

def test_with_fixture():
    """Test login with manually created fixture."""
    settings = get_settings()
    
    # Use test database
    test_db_url = settings.database_url.replace("aiutox_erp", "aiutox_erp_test")
    
    engine = create_engine(test_db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Create tenant
        tenant = Tenant(
            name="Test Tenant",
            slug="test-tenant",
        )
        db.add(tenant)
        db.flush()
        
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
        db.flush()
        db.refresh(user)
        
        print(f"Created user: {user.email}")
        print(f"User ID: {user.id}")
        print(f"Tenant ID: {user.tenant_id}")
        print(f"Full name: {user.full_name}")
        print(f"Password hash bytes: {password_hash.encode('utf-8')[:50]}...")
        
        # Test login
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": user.email,
                "password": password,
            },
        )
        
        print(f"Login status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.rollback()
        db.close()

if __name__ == "__main__":
    test_with_fixture()
