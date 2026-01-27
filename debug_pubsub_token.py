#!/usr/bin/env python3
"""Debug PubSub token creation."""

from app.core.db.deps import get_db
from app.core.auth import hash_password
from app.models.user import User
from app.models.tenant import Tenant
from tests.helpers import create_user_with_permission
from uuid import uuid4

def main():
    """Test directo del helper create_user_with_permission."""
    db = next(get_db())
    try:
        # Crear tenant
        tenant = Tenant(
            name=f'Test Tenant {uuid4().hex[:8]}',
            slug=f'test-tenant-{uuid4().hex[:8]}',
            is_active=True,
        )
        db.add(tenant)
        db.flush()

        # Crear usuario
        user = User(
            email=f'test-{uuid4().hex[:8]}@example.com',
            password_hash=hash_password('testpassword'),
            tenant_id=tenant.id,
            is_active=True,
        )
        db.add(user)
        db.flush()

        print(f'User ID: {user.id}')
        print(f'Tenant ID: {user.tenant_id}')

        # Crear headers con permisos pubsub
        headers = create_user_with_permission(db, user, 'pubsub', 'internal.viewer')
        print(f'Headers: {headers}')

        # Verificar el token
        if 'Authorization' in headers:
            token = headers['Authorization'].split(' ')[1]
            from app.core.auth.jwt import decode_token
            payload = decode_token(token)
            print(f'Token payload: {payload}')
            print(f'Permissions in token: {payload.get("permissions", [])}')

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
