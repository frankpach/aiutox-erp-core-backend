#!/usr/bin/env python
"""Test simple para el endpoint de tasks comments sin base de datos."""

import requests

# Token válido
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYWI5MDQyZC1hYmUxLTQ5OGEtYWM2Ny03MTA4ZjYyYjk2M2EiLCJ0ZW5hbnRfaWQiOiIzNmVhMWZjYS02YjJiLTQ2ZDQtODRlMS0xZjNiZGMxMzk2MGUiLCJyb2xlcyI6WyJvd25lciJdLCJwZXJtaXNzaW9ucyI6WyIqIl0sImV4cCI6MTc2OTQ2MzMwNCwidHlwZSI6ImFjY2VzcyIsImlhdCI6MTc2OTM3NjkwNH0.3XecwbPXAf05qgfLEa6QO7-CX8pv17UA4L4QC-_fCyU"
}

def test_tasks_comments_endpoint():
    """Test básico del endpoint de tasks comments."""

    # 1. Probar endpoint con task_id inexistente
    print("🔍 Test 1: GET /api/v1/tasks/{task_id}/comments con task_id inexistente")
    response = requests.get(
        "http://localhost:8000/api/v1/tasks/53518d30-1816-428c-9295-9f69ca522d0a/comments",
        headers=headers
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    # Verificar estructura de respuesta
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert "error" in data
    assert isinstance(data["data"], list)
    assert data["meta"]["total"] == 0
    print("✅ Test 1 pasado")

    # 2. Probar crear un comentario
    print("\n🔍 Test 2: POST /api/v1/tasks/{task_id}/comments")
    comment_data = {
        "content": "Test comment desde script",
        "mentions": []
    }

    response = requests.post(
        "http://localhost:8000/api/v1/tasks/53518d30-1816-428c-9295-9f69ca522d0a/comments",
        json=comment_data,
        headers=headers
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    assert response.status_code == 201
    created_comment = response.json()["data"]
    assert created_comment["content"] == "Test comment desde script"
    assert "id" in created_comment
    print("✅ Test 2 pasado")

    # 3. Probar listar comentarios después de crear uno
    print("\n🔍 Test 3: GET /api/v1/tasks/{task_id}/comments después de crear")
    response = requests.get(
        "http://localhost:8000/api/v1/tasks/53518d30-1816-428c-9295-9f69ca522d0a/comments",
        headers=headers
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) >= 1
    assert data["meta"]["total"] >= 1
    print("✅ Test 3 pasado")

    # 4. Probar endpoint general de comments para comparar
    print("\n🔍 Test 4: GET /api/v1/comments?entity_type=task&entity_id=...")
    response = requests.get(
        "http://localhost:8000/api/v1/comments?entity_type=task&entity_id=53518d30-1816-428c-9295-9f69ca522d0a",
        headers=headers
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data
    print("✅ Test 4 pasado")

    print("\n🎉 Todos los tests pasaron!")

if __name__ == "__main__":
    test_tasks_comments_endpoint()
