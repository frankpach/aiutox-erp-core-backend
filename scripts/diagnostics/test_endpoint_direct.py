"""Test directo del endpoint de comments."""

import requests

# Configuración
BASE_URL = "http://localhost:8000"
TASK_ID = "53518d30-1816-428c-9295-9f69ca522d0a"

# Token de autenticación (debes obtenerlo primero)
# Asumiendo que tienes un token válido
TOKEN = None  # Reemplazar con token real

def test_get_comments():
    """Test del endpoint GET /tasks/{task_id}/comments."""

    print("\n" + "="*80)
    print("TEST ENDPOINT GET COMMENTS")
    print("="*80 + "\n")

    # Primero, hacer login para obtener token
    print("1. LOGIN:")
    print("-" * 80)

    login_response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={
            "email": "admin@aiutox.com",
            "password": "admin123"
        }
    )

    print(f"Status: {login_response.status_code}")

    if login_response.status_code == 200:
        token = login_response.json()["data"]["access_token"]
        print(f"✅ Token obtenido: {token[:50]}...")

        # Test endpoint de comments
        print("\n2. GET COMMENTS:")
        print("-" * 80)

        headers = {
            "Authorization": f"Bearer {token}"
        }

        comments_url = f"{BASE_URL}/api/v1/tasks/{TASK_ID}/comments"
        print(f"URL: {comments_url}")

        response = requests.get(comments_url, headers=headers)

        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Response: {response.text[:500]}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Respuesta exitosa:")
            print(f"Total comments: {data.get('meta', {}).get('total', 0)}")
            print(f"Data: {data.get('data', [])}")
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
    else:
        print(f"❌ Login falló: {login_response.text}")

    print("\n" + "="*80)
    print("FIN DEL TEST")
    print("="*80 + "\n")


if __name__ == "__main__":
    test_get_comments()
