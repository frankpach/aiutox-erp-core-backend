#!/usr/bin/env python
"""Test para probar endpoint sin autenticación."""

import requests

def test_no_auth():
    """Probar endpoint sin autenticación."""

    base_url = "http://localhost:8000/api/v1/tasks"
    task_id = "53518d30-1816-428c-9295-9f69ca522d0a"

    print("🔍 Probando endpoint SIN autenticación...")
    response = requests.get(f"{base_url}/{task_id}/comments-no-auth")
    print(f"Status: {response.status_code}")
    print(f"Body: {response.json()}")

    print("\n✅ Test completado. Revisa la terminal de uvicorn para los prints.")

if __name__ == "__main__":
    test_no_auth()
