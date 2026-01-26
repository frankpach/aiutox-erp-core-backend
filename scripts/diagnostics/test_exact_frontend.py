#!/usr/bin/env python
"""Test comment endpoint exactly like frontend."""

import json

import requests

# Exact same data as frontend
task_id = "53518d30-1816-428c-9295-9f69ca522d0a"
url = f"http://localhost:8000/api/v1/tasks/{task_id}/comments"
data = {"content": "Test exacto como frontend", "mentions": []}

# Exact same headers as frontend
headers = {
    "Content-Type": "application/json; charset=utf-8",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYWI5MDQyZC1hYmUxLTQ5OGEtYWM2Ny03MTA4ZjYyYjk2M2EiLCJ0ZW5hbnRfaWQiOiIzNmVhMWZjYS02YjJiLTQ2ZDQtODRlMS0xZjNiZGMxMzk2MGUiLCJyb2xlcyI6WyJvd25lciJdLCJwZXJtaXNzaW9ucyI6WyIqIl0sImV4cCI6MTc2OTQ2MzMwNCwidHlwZSI6ImFjY2VzcyIsImlhdCI6MTc2OTM3NjkwNH0.3XecwbPXAf05qgfLEa6QO7-CX8pv17UA4L4QC-_fCyU",
    "Origin": "http://127.0.0.1:3000",
    "Referer": "http://127.0.0.1:3000/"
}

print("🔍 Testing EXACTLY like frontend...")
print(f"URL: {url}")
print(f"Headers: {json.dumps(headers, indent=2)}")
print(f"Data: {json.dumps(data, indent=2)}")
print("=" * 60)

try:
    # Send with cookies (like withCredentials: true)
    session = requests.Session()

    response = session.post(
        url,
        json=data,
        headers=headers,
        timeout=30  # Same timeout as frontend
    )

    print("\n✅ Response received!")
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")

    try:
        response_json = response.json()
        print(f"Body: {json.dumps(response_json, indent=2)}")
    except Exception:
        print(f"Body (raw): {response.text}")

    # Analysis
    if response.status_code == 201:
        print("\n🎉 SUCCESS! Comment created")
    elif response.status_code == 422:
        print("\n❌ VALIDATION ERROR")
        print("The backend is rejecting the request")
    else:
        print(f"\n⚠️ Unexpected status: {response.status_code}")

except requests.exceptions.Timeout:
    print("\n💥 TIMEOUT - Same as frontend!")
    print("The backend is hanging...")
except Exception as e:
    print(f"\n💥 ERROR: {e}")
