"""Test GET comments con debugging detallado."""

import requests

# Token válido
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYWI5MDQyZC1hYmUxLTQ5OGEtYWM2Ny03MTA4ZjYyYjk2M2EiLCJ0ZW5hbnRfaWQiOiIzNmVhMWZjYS02YjJiLTQ2ZDQtODRlMS0xZjNiZGMxMzk2MGUiLCJyb2xlcyI6WyJvd25lciJdLCJwZXJtaXNzaW9ucyI6WyIqIl0sImV4cCI6MTc2OTQ2MzMwNCwidHlwZSI6ImFjY2VzcyIsImlhdCI6MTc2OTM3NjkwNH0.3XecwbPXAf05qgfLEa6QO7-CX8pv17UA4L4QC-_fCyU"
}

task_id = "53518d30-1816-428c-9295-9f69ca522d0a"

print("\n" + "="*80)
print("TEST GET COMMENTS - DEBUGGING")
print("="*80 + "\n")

# 1. Verificar que el endpoint existe
print("1. Probando endpoint /test-order (debe funcionar):")
response = requests.get("http://localhost:8000/api/v1/tasks/test-order", headers=headers)
print(f"   Status: {response.status_code}")
print(f"   Body: {response.json()}\n")

# 2. Probar endpoint sin auth
print("2. Probando endpoint /{task_id}/comments-no-auth:")
response = requests.get(f"http://localhost:8000/api/v1/tasks/{task_id}/comments-no-auth", headers=headers)
print(f"   Status: {response.status_code}")
print(f"   Body: {response.json()}\n")

# 3. Probar endpoint GET comments real
print("3. Probando endpoint GET /{task_id}/comments:")
url = f"http://localhost:8000/api/v1/tasks/{task_id}/comments"
print(f"   URL: {url}")
response = requests.get(url, headers=headers)
print(f"   Status: {response.status_code}")
print(f"   Body: {response.json()}\n")

# 4. Verificar que los comentarios existen en BD
print("4. Verificando comentarios en BD con script diagnose_comments.py...")
print("   (Ejecutar: python scripts/diagnostics/diagnose_comments.py)\n")

print("="*80)
print("REVISAR LOGS DEL SERVIDOR BACKEND")
print("Buscar líneas con: [GET COMMENTS]")
print("="*80 + "\n")
