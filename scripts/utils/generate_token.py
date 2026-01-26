#!/usr/bin/env python
"""Generar un token JWT de prueba para desarrollo."""

from datetime import UTC, datetime, timedelta

import jwt

# Clave secreta del backend
SECRET_KEY = "your-secret-key-here-change-in-production"

# Payload del token con user ID real
payload = {
    "sub": "fab9042d-abe1-498a-ac67-7108f62b963a",  # User ID real de owner@aiutox.com
    "tenant_id": "36ea1fca-6b2b-46d4-84e1-1f3bdc13960e",  # Tenant ID del frontend
    "roles": ["owner"],
    "permissions": ["*"],
    "exp": datetime.now(tz=UTC) + timedelta(hours=24),  # Expira en 24 horas
    "type": "access",
    "iat": datetime.now(tz=UTC)
}

# Generar token
token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

print("Token generado:")
print(token)
print("\nUsa este token para probar los endpoints:")
