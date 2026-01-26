#!/usr/bin/env python
"""Test simple endpoint."""

import requests

# Token
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYWI5MDQyZC1hYmUxLTQ5OGEtYWM2Ny03MTA4ZjYyYjk2M2EiLCJ0ZW5hbnRfaWQiOiIzNmVhMWZjYS02YjJiLTQ2ZDQtODRlMS0xZjNiZGMxMzk2MGUiLCJyb2xlcyI6WyJvd25lciJdLCJwZXJtaXNzaW9ucyI6WyIqIl0sImV4cCI6MTc2OTQ2MzMwNCwidHlwZSI6ImFjY2VzcyIsImlhdCI6MTc2OTM3NjkwNH0.3XecwbPXAf05qgfLEa6QO7-CX8pv17UA4L4QC-_fCyU"
}

# Probar endpoint de prueba
print("🔍 Probando /test-order...")
response = requests.get("http://localhost:8000/api/v1/tasks/test-order", headers=headers)
print(f"Status: {response.status_code}")
print(f"Body: {response.json()}")
print()

# Probar endpoint comments
print("🔍 Probando /comments...")
response = requests.get("http://localhost:8000/api/v1/tasks/53518d30-1816-428c-9295-9f69ca522d0a/comments", headers=headers)
print(f"Status: {response.status_code}")
print(f"Body: {response.json()}")
