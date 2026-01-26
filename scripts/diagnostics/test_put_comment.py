"""Test PUT comment endpoint."""

import requests

# Token válido
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYWI5MDQyZC1hYmUxLTQ5OGEtYWM2Ny03MTA4ZjYyYjk2M2EiLCJ0ZW5hbnRfaWQiOiIzNmVhMWZjYS02YjJiLTQ2ZDQtODRlMS0xZjNiZGMxMzk2MGUiLCJyb2xlcyI6WyJvd25lciJdLCJwZXJtaXNzaW9ucyI6WyIqIl0sImV4cCI6MTc2OTM4Mjc5MywidHlwZSI6ImFjY2VzcyIsImlhdCI6MTc2OTM3OTE5M30.b_NHlb1cDPLIV4vXTgWHqqrGx7kZYN-3-O4vt5bAKDM"
}

task_id = "53518d30-1816-428c-9295-9f69ca522d0a"
comment_id = "fc2dc463-0fa3-4a7a-93f5-01385757727e"  # Comentario que existe

print("\n" + "="*80)
print("TEST PUT COMMENT")
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

# 2. Intentar actualizar el comentario
print(f"2. Actualizando comentario {comment_id}...")
update_data = {
    "content": "Contenido actualizado desde test script"
}
response = requests.put(
    f"http://localhost:8000/api/v1/tasks/{task_id}/comments/{comment_id}",
    headers=headers,
    json=update_data
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

# 3. Verificar que se actualizó
print("\n3. Verificando que se actualizó...")
response = requests.get(f"http://localhost:8000/api/v1/tasks/{task_id}/comments", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Total comentarios después de actualizar: {data['meta']['total']}")
    for comment in data['data']:
        if comment['id'] == comment_id:
            print(f"  - Comentario actualizado: {comment['content']}")

print("\n" + "="*80)
print("FIN DEL TEST")
print("="*80 + "\n")
