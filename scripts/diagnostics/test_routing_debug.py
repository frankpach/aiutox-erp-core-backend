#!/usr/bin/env python
"""Test para depurar el routing de endpoints."""

import requests

# Token válido
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYWI5MDQyZC1hYmUxLTQ5OGEtYWM2Ny03MTA4ZjYyYjk2M2EiLCJ0ZW5hbnRfaWQiOiIzNmVhMWZjYS02YjJiLTQ2ZDQtODRlMS0xZjNiZGMxMzk2MGUiLCJyb2xlcyI6WyJvd25lciJdLCJwZXJtaXNzaW9ucyI6WyIqIl0sImV4cCI6MTc2OTQ2MzMwNCwidHlwZSI6ImFjY2VzcyIsImlhdCI6MTc2OTM3NjkwNH0.3XecwbPXAf05qgfLEa6QO7-CX8pv17UA4L4QC-_fCyU"
}

def test_routing():
    """Probar diferentes endpoints para verificar routing."""

    base_url = "http://localhost:8000/api/v1/tasks"

    # Test 1: Endpoint sin parámetros
    print("1️⃣ Probando /test-order (sin parámetros)...")
    response = requests.get(f"{base_url}/test-order", headers=headers)
    print(f"   Status: {response.status_code}")
    print(f"   Body: {response.json()}")

    # Test 2: Endpoint con parámetro genérico
    print("\n2️⃣ Probando /{task_id}/test-param...")
    response = requests.get(f"{base_url}/53518d30-1816-428c-9295-9f69ca522d0a/test-param", headers=headers)
    print(f"   Status: {response.status_code}")
    print(f"   Body: {response.json()}")

    # Test 3: Endpoint específico para el task_id
    print("\n3️⃣ Probando /53518d30-1816-428c-9295-9f69ca522d0a/test-specific...")
    response = requests.get(f"{base_url}/53518d30-1816-428c-9295-9f69ca522d0a/test-specific", headers=headers)
    print(f"   Status: {response.status_code}")
    print(f"   Body: {response.json()}")

    # Test 4: El endpoint problemático
    print("\n4️⃣ Probando /{task_id}/comments (el endpoint problemático)...")
    response = requests.get(f"{base_url}/53518d30-1816-428c-9295-9f69ca522d0a/comments", headers=headers)
    print(f"   Status: {response.status_code}")
    print(f"   Body: {response.json()}")

    # Test 5: Probar con un task_id diferente
    print("\n5️⃣ Probando /{task_id}/comments con task_id diferente...")
    response = requests.get(f"{base_url}/12345678-1234-1234-1234-123456789012/comments", headers=headers)
    print(f"   Status: {response.status_code}")
    print(f"   Body: {response.json()}")

    print("\n✅ Tests completados. Revisa la terminal de uvicorn para los prints.")

if __name__ == "__main__":
    test_routing()
