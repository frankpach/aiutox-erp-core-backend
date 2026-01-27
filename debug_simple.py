#!/usr/bin/env python3
"""Simple debug script for pubsub permissions."""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

logging.basicConfig(level=logging.DEBUG)

def main():
    """Test permission creation directly."""
    from uuid import uuid4

    from app.core.auth import hash_password
    from app.core.db.session import get_db_session
    from app.models.module_role import ModuleRole
    from app.models.tenant import Tenant
    from app.models.user import User
    from app.services.auth_service import AuthService
    from app.services.permission_service import PermissionService

    # Get database session
    db = next(get_db_session())

    try:
        # Create tenant
        tenant = Tenant(
            id=uuid4(),
            name="Debug Tenant",
            slug="debug-tenant",
            is_active=True
        )
        db.add(tenant)
        db.flush()

        # Create user
        password = "test_password_123"
        password_hash = hash_password(password)
        user = User(
            id=uuid4(),
            tenant_id=tenant.id,
            email="debug@example.com",
            password_hash=password_hash,
            full_name="Debug User",
            is_active=True
        )
        db.add(user)
        db.flush()

        # Create module role
        module_role = ModuleRole(
            user_id=user.id,
            module="pubsub",
            role_name="internal.viewer",
            granted_by=user.id
        )
        db.add(module_role)
        db.commit()

        print(f"Created user: {user.id}")
        print(f"Created module role: {module_role.module}.{module_role.role_name}")

        # Check permissions
        permission_service = PermissionService(db)
        permissions = permission_service.get_effective_permissions(user.id)
        print(f"User permissions: {permissions}")
        print(f"Has pubsub.view: {'pubsub.view' in permissions}")

        # Create token
        auth_service = AuthService(db)
        token = auth_service.create_access_token_for_user(user)
        print(f"Token created: {token[:50]}...")

        # Test token decode
        from app.core.auth.jwt import decode_token
        payload = decode_token(token)
        print(f"Token payload: {payload}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
