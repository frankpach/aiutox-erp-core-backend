#!/usr/bin/env python
"""Test para probar endpoint con token."""

import requests


def test_with_token():
    """Probar endpoint con token de autenticación."""

    base_url = "http://localhost:8000/api/v1/tasks"
    task_id = "53518d30-1816-428c-9295-9f69ca522d0a"

    # Token válido
    headers = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYWI5MDQyZC1hYmUxLTQ5OGEtYWM2Ny03MTA4ZjYyYjk2M2EiLCJ0ZW5hbnRfaWQiOiIzNmVhMWZjYS02YjJiLTQ2ZDQtODRlMS0xZjNiZGMxMzk2MGUiLCJyb2xlcyI6WyJvd25lciJdLCJwZXJtaXNzaW9ucyI6WyIqIl0sImV4cCI6MTc2OTQ2MzMwNCwidHlwZSI6ImFjY2VzcyIsImlhdCI6MTc2OTM3NjkwNH0.3XecwbPXAf05qgfLEa6QO7-CX8pv17UA4L4QC-_fCyU"
    }

    print("🔍 Probando endpoint CON token...")
    response = requests.get(f"{base_url}/{task_id}/comments", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Body: {response.json()}")

    print("\n✅ Test completado. Revisa la terminal de uvicorn para los prints.")

if __name__ == "__main__":
    test_with_token()
