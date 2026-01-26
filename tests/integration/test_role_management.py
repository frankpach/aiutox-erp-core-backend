"""Integration tests for role management operations."""

from uuid import uuid4

import pytest
from fastapi import status

from app.core.auth import hash_password
from app.models.user import User
from app.models.user_role import UserRole
from app.services.auth_service import AuthService


class TestRoleManagement:
    """Test suite for role management functionality."""

    def test_list_available_roles_requires_authentication(
        self, client_with_db, db_session
    ):
        """Test that listing available roles requires authentication."""
        # Act: Try to list roles without authentication
        response = client_with_db.get("/api/v1/auth/roles")

        # Assert: Should be denied
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_available_roles_with_authentication(
        self, client_with_db, db_session, test_user
    ):
        """Test that authenticated user can list available roles."""
        # Arrange: Authenticated user
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: List roles
        response = client_with_db.get(
            "/api/v1/auth/roles",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "meta" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0

        # Verify roles structure
        role = data["data"][0]
        assert "role" in role
        assert "permissions" in role

    def test_get_user_roles_requires_auth_manage_users(
        self, client_with_db, db_session, test_user
    ):
        """Test that getting user roles requires auth.manage_users permission."""
        # Arrange: User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to get user roles
        response = client_with_db.get(
            f"/api/v1/auth/roles/{test_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_user_roles_with_permission(
        self, client_with_db, db_session, test_user
    ):
        """Test that admin can get user roles."""
        # Arrange: Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        # Assign another role to test_user
        viewer_role = UserRole(
            user_id=test_user.id,
            role="viewer",
            granted_by=test_user.id,
        )
        db_session.add(viewer_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Get user roles
        response = client_with_db.get(
            f"/api/v1/auth/roles/{test_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "roles" in data
        assert "total" in data
        assert data["total"] == 2
        role_names = [role["role"] for role in data["roles"]]
        assert "admin" in role_names
        assert "viewer" in role_names

    def test_assign_role_requires_auth_manage_roles(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that assigning role requires auth.manage_roles permission."""
        # Arrange: User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Create target user
        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        # Act: Try to assign role
        response = client_with_db.post(
            f"/api/v1/auth/roles/{target_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"role": "viewer"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_assign_role_with_permission(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that admin can assign role."""
        # Arrange: Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        # Create target user
        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Assign role
        response = client_with_db.post(
            f"/api/v1/auth/roles/{target_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"role": "viewer"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["role"] == "viewer"
        assert data["granted_by"] == str(test_user.id)

    def test_assign_role_duplicate(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that assigning duplicate role fails."""
        # Arrange: Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        # Create target user with existing role
        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        existing_role = UserRole(
            user_id=target_user.id,
            role="viewer",
            granted_by=test_user.id,
        )
        db_session.add(existing_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to assign same role again
        response = client_with_db.post(
            f"/api/v1/auth/roles/{target_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"role": "viewer"},
        )

        # Assert: Should fail
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "ROLE_ALREADY_ASSIGNED"

    def test_assign_role_invalid_role(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that assigning invalid role fails."""
        # Arrange: Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        # Create target user
        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to assign invalid role
        response = client_with_db.post(
            f"/api/v1/auth/roles/{target_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"role": "invalid_role"},
        )

        # Assert: Should fail
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_remove_role_requires_auth_manage_roles(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that removing role requires auth.manage_roles permission."""
        # Arrange: User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Create target user with role
        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        role = UserRole(
            user_id=target_user.id,
            role="viewer",
            granted_by=test_user.id,
        )
        db_session.add(role)
        db_session.commit()

        # Act: Try to remove role
        response = client_with_db.delete(
            f"/api/v1/auth/roles/{target_user.id}/viewer",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_remove_role_with_permission(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that admin can remove role."""
        # Arrange: Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        # Create target user with role
        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        role = UserRole(
            user_id=target_user.id,
            role="viewer",
            granted_by=test_user.id,
        )
        db_session.add(role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Remove role
        response = client_with_db.delete(
            f"/api/v1/auth/roles/{target_user.id}/viewer",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "message" in data["data"]

        # Verify role is removed
        remaining_roles = (
            db_session.query(UserRole)
            .filter(UserRole.user_id == target_user.id, UserRole.role == "viewer")
            .first()
        )
        assert remaining_roles is None

    def test_remove_role_not_assigned(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that removing non-assigned role returns 404."""
        # Arrange: Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        # Create target user without the role
        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to remove non-assigned role
        response = client_with_db.delete(
            f"/api/v1/auth/roles/{target_user.id}/viewer",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return 404
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "ROLE_NOT_FOUND"

    def test_role_management_multi_tenant_isolation(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that role management is isolated per tenant."""
        from app.models.tenant import Tenant

        # Arrange: Create second tenant and user
        tenant2 = Tenant(
            name="Test Tenant 2",
            slug=f"test-tenant-2-{uuid4().hex[:8]}",
        )
        db_session.add(tenant2)
        db_session.commit()

        user2 = User(
            email=f"user2-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="User 2",
            tenant_id=tenant2.id,
            is_active=True,
        )
        db_session.add(user2)
        db_session.commit()

        # Assign admin role to test_user
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to assign role to user from different tenant
        response = client_with_db.post(
            f"/api/v1/auth/roles/{user2.id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"role": "viewer"},
        )

        # Assert: Should be denied (tenant mismatch)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTH_TENANT_MISMATCH"

