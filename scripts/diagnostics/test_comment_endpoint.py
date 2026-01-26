#!/usr/bin/env python
"""Script to test comment endpoint directly."""

import requests
import json

# Test data
task_id = "53518d30-1816-428c-9295-9f69ca522d0a"
url = f"http://localhost:8000/api/v1/tasks/{task_id}/comments"

# Test without auth first
print("🧪 Testing comment endpoint...")
print(f"URL: {url}")
print("=" * 60)

# Test 1: Simple content
data = {"content": "Test comment from Python script"}
headers = {"Content-Type": "application/json"}

print("\n📤 Sending request:")
print(f"Method: POST")
print(f"Headers: {headers}")
print(f"Body: {json.dumps(data, indent=2)}")

try:
    response = requests.post(url, json=data, headers=headers)

    print(f"\n📥 Response:")
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")

    try:
        response_json = response.json()
        print(f"Body: {json.dumps(response_json, indent=2)}")
    except:
        print(f"Body (raw): {response.text}")

    # Analysis
    if response.status_code == 422:
        print("\n❌ VALIDATION ERROR (422)")
        print("The request is being rejected before reaching the endpoint.")
        print("Possible causes:")
        print("1. FastAPI is validating against a schema somewhere")
        print("2. There's a middleware interfering")
        print("3. The endpoint signature is causing issues")

    elif response.status_code == 401:
        print("\n🔒 AUTHENTICATION ERROR (401)")
        print("Authentication is required")

    elif response.status_code == 200:
        print("\n✅ SUCCESS!")
        print("Comment created successfully")

    else:
        print(f"\n⚠️ UNEXPECTED STATUS: {response.status_code}")

except requests.exceptions.ConnectionError:
    print("\n💥 CONNECTION ERROR")
    print("Backend is not running or not accessible")

except Exception as e:
    print(f"\n💥 ERROR: {e}")

print("\n" + "=" * 60)
print("🔍 Next steps:")
print("1. Check backend logs for [VALIDATION_ERROR] messages")
print("2. If 422 persists, check FastAPI's automatic validation")
print("3. Consider using a different endpoint signature")
