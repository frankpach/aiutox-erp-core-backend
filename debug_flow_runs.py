#!/usr/bin/env python3
"""Debug script for flow runs stats endpoint."""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

logging.basicConfig(level=logging.DEBUG)

def main():
    """Test flow runs stats endpoint."""
    from uuid import uuid4

    from app.core.auth import hash_password
    from app.core.auth.jwt import create_access_token
    from app.core.db.deps import get_db
    from app.core.flow_runs.service import FlowRunService
    from app.models.module_role import ModuleRole
    from app.models.tenant import Tenant
    from app.models.user import User

    # Get test database
    db = next(get_db())

    try:
        # Create test tenant
        tenant = Tenant(
            name=f"Test Tenant {uuid4().hex[:8]}",
            slug=f"test-tenant-{uuid4().hex[:8]}",
            is_active=True,
        )
        db.add(tenant)
        db.flush()

        # Create test user
        password = "test_password_123"
        password_hash = hash_password(password)
        user = User(
            email=f"test-{uuid4().hex[:8]}@example.com",
            password_hash=password_hash,
            full_name="Test User",
            tenant_id=tenant.id,
            is_active=True,
        )
        db.add(user)
        db.flush()

        # Create module role
        module_role = ModuleRole(
            user_id=user.id,
            module="flow_runs",
            role_name="internal.viewer",
            granted_by=user.id,
        )
        db.add(module_role)
        db.commit()

        # Create auth token
        token_data = {
            "sub": str(user.id),
            "tenant_id": str(tenant.id),
            "roles": [],
            "permissions": ["flow_runs.view"],
            "exp": 1769532611,  # Future timestamp
            "iat": 1769532611,
            "type": "access",
        }
        token = create_access_token(token_data)
        auth_headers = {"Authorization": f"Bearer {token}"}

        print(f"Created user: {user.id}")
        print(f"Tenant: {tenant.id}")
        print(f"Auth headers: {auth_headers}")

        # Test service directly
        service = FlowRunService(db)
        print("Testing FlowRunService.get_flow_runs_stats...")

        try:
            stats = service.get_flow_runs_stats(user.tenant_id)
            print(f"Stats result: {stats}")
        except Exception as e:
            print(f"Service error: {e}")
            import traceback
            traceback.print_exc()

    finally:
        db.close()

if __name__ == "__main__":
    main()
