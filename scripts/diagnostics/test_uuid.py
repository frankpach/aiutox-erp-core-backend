#!/usr/bin/env python
"""Test if task_id is valid UUID."""

from uuid import UUID

import requests

# Task ID from frontend
task_id = "53518d30-1816-428c-9295-9f69ca522d0a"

try:
    uuid_obj = UUID(task_id)
    print(f"✅ Task ID is valid UUID: {uuid_obj}")
    print(f"   Version: {uuid_obj.version}")
    print(f"   Variant: {uuid_obj.variant}")
except ValueError as e:
    print(f"❌ Task ID is NOT valid UUID: {e}")

# Test the endpoint directly

url = f"http://localhost:8000/api/v1/tasks/{task_id}/comments"
data = {"content": "Test comment", "mentions": []}

print("\n🧪 Testing endpoint...")
print(f"URL: {url}")
print(f"Data: {data}")

try:
    response = requests.post(url, json=data, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYWI5MDQyZC1hYmUxLTQ5OGEtYWM2Ny03MTA4ZjYyYjk2M2EiLCJ0ZW5hbnRfaWQiOiIzNmVhMWZjYS02YjJiLTQ2ZDQtODRlMS0xZjNiZGMxMzk2MGUiLCJyb2xlcyI6WyJvd25lciJdLCJwZXJtaXNzaW9ucyI6WyIqIl0sImV4cCI6MTc2OTM3NjQyMCwidHlwZSI6ImFjY2VzcyIsImlhdCI6MTc2OTM3MjgyMH0.Isgodk00EAcAyn7vjLCfsvDF4z8iGgHjpJxKbaNPh_g"
    })

    print(f"\nStatus: {response.status_code}")
    print(f"Response: {response.text}")

except Exception as e:
    print(f"\nError: {e}")
