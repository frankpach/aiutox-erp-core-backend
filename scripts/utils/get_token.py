#!/usr/bin/env python
"""Test para obtener un token válido."""

import requests

# Credenciales del sistema
credentials = [
    {"email": "owner@aiutox.com", "password": "owner123"},
    {"email": "owner@aiutox.com", "password": "admin123"},
    {"email": "owner@aiutox.com", "password": "password"},
]

for cred in credentials:
    print("\nProbando con:", cred['email'])
    response = requests.post(
        "http://localhost:8000/api/v1/auth/login",
        json=cred
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        token = response.json()["data"]["access_token"]
        print(f"✅ Token obtenido!")
        print(f"Token: {token[:50]}...")

        # Probar listar comentarios
        task_id = "53518d30-1816-428c-9295-9f69ca522d0a"
        headers = {"Authorization": f"Bearer {token}"}
        comments_response = requests.get(
            f"http://localhost:8000/api/v1/tasks/{task_id}/comments",
            headers=headers
        )
        print(f"Comments Status: {comments_response.status_code}")
        print(f"Comments Response: {comments_response.json()}")
        break
    else:
        print(f"❌ Error: {response.json()}")
