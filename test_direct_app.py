#!/usr/bin/env python3
"""Test the FastAPI app directly without test client."""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app

def test_direct_app():
    """Test app directly without pytest fixtures."""
    # Create a fresh test client
    client = TestClient(app)
    
    # Test login with simple credentials
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "wrong"},
    )
    
    print(f"Status: {response.status_code}")
    print(f"Headers: {list(response.headers.keys())}")
    print(f"Response: {response.text[:200]}")
    
    # Check for problematic bytes in headers
    for key, value in response.headers.items():
        try:
            if isinstance(value, bytes):
                value.decode('utf-8')
            elif isinstance(value, str):
                value.encode('utf-8')
        except (UnicodeDecodeError, UnicodeEncodeError) as e:
            print(f"Problematic header: {key} = {value!r}")
            print(f"Error: {e}")

if __name__ == "__main__":
    test_direct_app()
