"""Integration tests for authentication endpoints with debugging."""

import pytest
from fastapi import status

from app.core.auth import decode_token


def test_login_success_debug(client, test_user):
    """Test that login endpoint returns both tokens on success - with debugging."""
    print(f"\n=== DEBUG LOGIN TEST ===")
    print(f"Test user email: {test_user.email}")
    print(f"Test user password: {test_user._plain_password}")
    print(f"Test user full name: {test_user.full_name}")
    print(f"Test user ID: {test_user.id}")
    print(f"Test user tenant ID: {test_user.tenant_id}")
    
    try:
        print("Making login request...")
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": test_user._plain_password,
            },
        )
        print(f"Response status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        # Try to get raw response text first
        print("Getting response text...")
        response_text = response.text
        print(f"Response text (first 200 chars): {response_text[:200]}")
        print(f"Response text length: {len(response_text)}")
        
        # Try to get bytes
        print("Getting response content as bytes...")
        response_bytes = response.content
        print(f"Response bytes (first 50): {response_bytes[:50]}")
        print(f"Response bytes length: {len(response_bytes)}")
        
        # Check for problematic bytes
        if b'\xed' in response_bytes:
            print("Found byte 0xed in response!")
            positions = [i for i, b in enumerate(response_bytes) if b == 0xed]
            print(f"Positions of 0xed: {positions}")
            
        print("Trying to parse JSON...")
        data = response.json()
        print("JSON parsing successful!")
        
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
        decoded = decode_token(token_data["access_token"])
        assert decoded is not None
        assert decoded["sub"] == str(test_user.id)
        
        print("Test passed!")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
        raise
