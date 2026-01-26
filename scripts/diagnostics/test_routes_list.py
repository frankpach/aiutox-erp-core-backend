#!/usr/bin/env python
"""Script para listar todas las rutas de la API."""

import requests

def list_routes():
    """Listar todas las rutas disponibles."""

    # Obtener el OpenAPI spec
    response = requests.get("http://localhost:8000/openapi.json")

    if response.status_code == 200:
        openapi = response.json()

        print("📋 TODAS LAS RUTAS DISPONIBLES:")
        print("="*80)

        for path, methods in openapi["paths"].items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    tags = details.get("tags", [])
                    summary = details.get("summary", "")

                    # Buscar rutas con "comments"
                    if "comments" in path.lower() or "comments" in summary.lower():
                        print(f"🔍 [ENCONTRADO] {method.upper():<8} {path:<60} | Tags: {tags}")
                        print(f"   └─ {summary}")

        print("\n" + "="*80)
        print("🔍 BUSCANDO ESPECÍFICAMENTE RUTAS DE COMMENTS:")
        print("="*80)

        for path, methods in openapi["paths"].items():
            if "comments" in path.lower():
                for method, details in methods.items():
                    if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                        tags = details.get("tags", [])
                        summary = details.get("summary", "")
                        print(f"  {method.upper():<8} {path:<60} | Tags: {tags}")
                        print(f"    └─ {summary}")
    else:
        print(f"❌ Error obteniendo OpenAPI: {response.status_code}")

if __name__ == "__main__":
    list_routes()
