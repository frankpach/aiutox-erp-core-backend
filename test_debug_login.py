#!/usr/bin/env python3
"""Debug script to isolate the Unicode issue in login."""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app

def test_minimal_login():
    """Test minimal login to isolate Unicode issue."""
    client = TestClient(app)
    
    # Try a simple request first
    try:
        response = client.get("/")
        print(f"Root endpoint status: {response.status_code}")
        print(f"Root response: {response.text[:200]}")
    except Exception as e:
        print(f"Root endpoint error: {e}")
        return
    
    # Try login with minimal data
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrong_password"},
        )
        print(f"Login status: {response.status_code}")
        print(f"Login response text: {response.text[:200]}")
        print(f"Login response headers: {dict(response.headers)}")
    except Exception as e:
        print(f"Login error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_minimal_login()
