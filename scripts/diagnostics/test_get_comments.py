#!/usr/bin/env python
"""Probar el endpoint GET /comments con el nuevo token."""

import requests

# Token recién generado
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYWI5MDQyZC1hYmUxLTQ5OGEtYWM2Ny03MTA4ZjYyYjk2M2EiLCJ0ZW5hbnRfaWQiOiIzNmVhMWZjYS02YjJiLTQ2ZDQtODRlMS0xZjNiZGMxMzk2MGUiLCJyb2xlcyI6WyJvd25lciJdLCJwZXJtaXNzaW9ucyI6WyIqIl0sImV4cCI6MTc2OTQ2MzMwNCwidHlwZSI6ImFjY2VzcyIsImlhdCI6MTc2OTM3NjkwNH0.3XecwbPXAf05qgfLEa6QO7-CX8pv17UA4L4QC-_fCyU"

# Task ID
task_id = "53518d30-1816-428c-9295-9f69ca522d0a"

# Headers
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Probar GET /comments
print("🔍 Probando GET /comments...")
url = f"http://localhost:8000/api/v1/tasks/{task_id}/comments"
print(f"URL: {url}")

response = requests.get(url, headers=headers)
print(f"\n✅ Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"📊 Total comentarios: {data['meta']['total']}")
    if data['data']:
        print("📝 Comentarios encontrados:")
        for comment in data['data']:
            print(f"  - ID: {comment['id']}")
            print(f"    Content: {comment['content']}")
            print(f"    User ID: {comment['user_id']}")
            print(f"    Created: {comment['created_at']}")
    else:
        print("❌ No se encontraron comentarios")
else:
    print(f"❌ Error: {response.json()}")

print("\n" + "="*60)
print("📋 Revisa la terminal del backend para ver los logs [LIST_COMMENTS]")
