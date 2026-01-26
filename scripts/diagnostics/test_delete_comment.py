"""Test DELETE comment endpoint."""

import requests

# Token válido
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYWI5MDQyZC1hYmUxLTQ5OGEtYWM2Ny03MTA4ZjYyYjk2M2EiLCJ0ZW5hbnRfaWQiOiIzNmVhMWZjYS02YjJiLTQ2ZDQtODRlMS0xZjNiZGMxMzk2MGUiLCJyb2xlcyI6WyJvd25lciJdLCJwZXJtaXNzaW9ucyI6WyIqIl0sImV4cCI6MTc2OTM4Mjc5MywidHlwZSI6ImFjY2VzcyIsImlhdCI6MTc2OTM3OTE5M30.b_NHlb1cDPLIV4vXTgWHqqrGx7kZYN-3-O4vt5bAKDM"
}

task_id = "53518d30-1816-428c-9295-9f69ca522d0a"
comment_id = "0dae89ae-e5ea-49d5-bf1a-50bfd4081423"

print("\n" + "="*80)
print("TEST DELETE COMMENT")
print("="*80 + "\n")

# 1. Primero obtener los comentarios para ver si existe
print("1. Obteniendo comentarios de la tarea...")
response = requests.get(f"http://localhost:8000/api/v1/tasks/{task_id}/comments", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Total comentarios: {data['meta']['total']}")
    for comment in data['data']:
        print(f"  - ID: {comment['id']}")
        print(f"    Content: {comment['content'][:50]}...")
        print()

# 2. Intentar eliminar el comentario
print(f"2. Eliminando comentario {comment_id}...")
response = requests.delete(f"http://localhost:8000/api/v1/tasks/{task_id}/comments/{comment_id}", headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

# 3. Verificar que se eliminó
print("\n3. Verificando que se eliminó...")
response = requests.get(f"http://localhost:8000/api/v1/tasks/{task_id}/comments", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Total comentarios después de eliminar: {data['meta']['total']}")

print("\n" + "="*80)
print("FIN DEL TEST")
print("="*80 + "\n")
