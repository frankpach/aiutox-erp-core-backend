#!/usr/bin/env python3
"""Debug script to test pytest environment."""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def test_pytest_environment():
    """Test pytest environment directly."""
    import pytest
    from fastapi.testclient import TestClient
    from app.main import app
    
    # Create pytest fixtures manually
    sys.path.insert(0, str(backend_dir / "tests"))
    
    try:
        # Import conftest to get fixtures
        import conftest
        
        # Create test app
        client = TestClient(app)
        
        # Try a simple request
        response = client.get("/")
        print(f"Root request: {response.status_code}")
        
        # Try login without fixtures
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrong"},
        )
        print(f"Login without user: {response.status_code}")
        print(f"Response: {response.text[:100]}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pytest_environment()
