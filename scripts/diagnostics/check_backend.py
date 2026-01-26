#!/usr/bin/env python
"""Simple test to check if backend is responding."""

import socket

def check_backend():
    """Check if backend is running on localhost:8000."""
    try:
        # Try to connect to the backend
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5 second timeout
        result = sock.connect_ex(('localhost', 8000))
        sock.close()

        if result == 0:
            print("✅ Backend is RUNNING on localhost:8000")
            return True
        else:
            print("❌ Backend is NOT running on localhost:8000")
            print(f"   Connection result: {result}")
            return False
    except TimeoutError:
        print("❌ Connection TIMEOUT - Backend might be hanging")
        return False
    except Exception as e:
        print(f"❌ Error checking backend: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Checking backend status...")
    print("=" * 50)

    if check_backend():
        print("\n🎯 Backend is accessible")
        print("   The issue might be with the endpoint itself")
    else:
        print("\n💥 Backend is not accessible")
        print("   Possible causes:")
        print("   1. Backend is not running")
        print("   2. Backend is frozen/hanging")
        print("   3. Port 8000 is blocked")
        print("\n🔧 Try:")
        print("   - Restart the backend: uvicorn app.main:app --reload")
        print("   - Check for errors in the backend terminal")
        print("   - Check if another process is using port 8000")
