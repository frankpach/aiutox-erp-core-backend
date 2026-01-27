#!/usr/bin/env python3
"""Debug script to test pubsub permissions."""

import logging

from app.core.auth.jwt import decode_token
from app.services.permission_service import PermissionService
from tests.helpers import create_user_with_permission

logging.basicConfig(level=logging.DEBUG)

def test_pubsub_permissions():
    """Test pubsub permissions creation and validation."""

    # Import test fixtures
    from tests.conftest import create_test_tenant, create_test_user, get_test_db
    # Get test database
    db = next(get_test_db())

    try:
        # Create test tenant and user
        tenant = create_test_tenant(db)
        user = create_test_user(db, tenant)

        print(f"Created user: {user.id}")

        # Create permission
        headers = create_user_with_permission(db, user, "pubsub", "internal.viewer")
        print(f"Headers created: {headers}")

        # Decode token to verify permissions
        token = headers["Authorization"].split(" ")[1]
        payload = decode_token(token)
        print(f"Token payload: {payload}")

        # Check permissions directly
        permission_service = PermissionService(db)
        permissions = permission_service.get_effective_permissions(user.id)
        print(f"User permissions: {permissions}")
        print(f"Has pubsub.view: {'pubsub.view' in permissions}")

    finally:
        db.close()

if __name__ == "__main__":
    test_pubsub_permissions()
