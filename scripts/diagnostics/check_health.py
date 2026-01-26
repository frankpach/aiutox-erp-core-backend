#!/usr/bin/env python
"""Check backend health."""

import socket

import requests

def check_backend_health():
    """Check if backend is responding."""
    print("🔍 Checking backend health...")

    # 1. Check if port is open
    print("\n1. Checking port 8000...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', 8000))
        sock.close()

        if result == 0:
            print("✅ Port 8000 is open")
        else:
            print(f"❌ Port 8000 is closed: {result}")
            return False
    except Exception as e:
        print(f"❌ Error checking port: {e}")
        return False

    # 2. Check health endpoint
    print("\n2. Checking /health endpoint...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=3)
        print(f"✅ Health endpoint responded: {response.status_code}")
        print(f"   Response: {response.text}")
    except requests.exceptions.Timeout:
        print("❌ Health endpoint TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
        return False

    # 3. Check root endpoint
    print("\n3. Checking root endpoint...")
    try:
        response = requests.get("http://localhost:8000/", timeout=3)
        print(f"✅ Root endpoint responded: {response.status_code}")
    except requests.exceptions.Timeout:
        print("❌ Root endpoint TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
        return False

    return True

if __name__ == "__main__":
    if check_backend_health():
        print("\n✅ Backend appears to be healthy")
        print("\n🔍 The issue might be with the specific endpoint")
        print("   - Check if there's an infinite loop in the endpoint")
        print("   - Check if database is locked")
        print("   - Check if there's a deadlock")
    else:
        print("\n❌ Backend is NOT healthy")
        print("\n🔧 Try:")
        print("   1. Restart the backend")
        print("   2. Check for errors in backend terminal")
        print("   3. Check if another process is using port 8000")
