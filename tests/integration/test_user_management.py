"""Integration tests for user management CRUD operations."""

from uuid import uuid4

import pytest
from fastapi import status

from app.core.auth import hash_password
from app.models.user import User
from app.models.user_role import UserRole
from app.services.auth_service import AuthService


class TestUserManagement:
    """Test suite for user management functionality."""

    def test_list_users_requires_auth_manage_users(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that listing users requires auth.manage_users permission."""
        # Arrange: User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to list users
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"

    def test_list_users_with_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that admin can list users."""
        # Arrange: Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: List users
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "meta" in data
        assert isinstance(data["data"], list)
        assert data["meta"]["total"] >= 1  # At least test_user

    def test_create_user_requires_auth_manage_users(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that creating user requires auth.manage_users permission."""
        # Arrange: User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to create user
        response = client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "email": f"new-{uuid4().hex[:8]}@example.com",
                "password": "password123",
                "tenant_id": str(test_tenant.id),
            },
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_user_with_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that admin can create user."""
        # Arrange: Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        new_email = f"new-{uuid4().hex[:8]}@example.com"

        # Act: Create user
        response = client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "email": new_email,
                "password": "password123",
                "tenant_id": str(test_tenant.id),
            },
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "data" in data
        assert data["data"]["email"] == new_email
        assert data["data"]["is_active"] is True

    def test_create_user_duplicate_email(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that creating user with duplicate email fails."""
        # Arrange: Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to create user with existing email
        response = client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "email": test_user.email,
                "password": "password123",
                "tenant_id": str(test_tenant.id),
            },
        )

        # Assert: Should fail
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data["detail"]
        assert "USER_ALREADY_EXISTS" in data["detail"]["error"]["code"]

    def test_get_user_requires_auth_manage_users(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that getting user requires auth.manage_users permission."""
        # Arrange: User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to get user
        response = client.get(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_user_with_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that admin can get user."""
        # Arrange: Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Get user
        response = client.get(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["id"] == str(test_user.id)
        assert data["data"]["email"] == test_user.email

    def test_get_user_not_found(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that getting non-existent user returns 404."""
        # Arrange: Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        fake_id = uuid4()

        # Act: Get non-existent user
        response = client.get(
            f"/api/v1/users/{fake_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return 404
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "USER_NOT_FOUND"

    def test_update_user_requires_auth_manage_users(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that updating user requires auth.manage_users permission."""
        # Arrange: User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to update user
        response = client.patch(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"full_name": "Updated Name"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_user_with_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that admin can update user."""
        # Arrange: Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Update user
        response = client.patch(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"full_name": "Updated Name"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["full_name"] == "Updated Name"

    def test_delete_user_requires_auth_manage_users(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that deleting user requires auth.manage_users permission."""
        # Arrange: User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to delete user
        response = client.delete(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_user_with_permission_soft_delete(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that admin can soft delete user (sets is_active=False)."""
        # Arrange: Create another user to delete
        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(target_user)
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

        # Act: Delete user
        response = client.delete(
            f"/api/v1/users/{target_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data

        # Verify user is soft deleted (is_active=False)
        db_session.refresh(target_user)
        assert target_user.is_active is False

    def test_list_users_pagination(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that listing users supports pagination."""
        # Arrange: Create multiple users
        for i in range(5):
            user = User(
                email=f"user{i}-{uuid4().hex[:8]}@example.com",
                password_hash=hash_password("password123"),
                full_name=f"User {i}",
                tenant_id=test_tenant.id,
                is_active=True,
            )
            db_session.add(user)
        db_session.commit()

        # Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: List users with pagination
        response = client.get(
            "/api/v1/users?page=1&page_size=3",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed with pagination
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "meta" in data
        assert len(data["data"]) == 3  # page_size
        assert data["meta"]["page"] == 1
        assert data["meta"]["page_size"] == 3
        assert data["meta"]["total"] >= 6  # test_user + 5 new users

    def test_user_management_multi_tenant_isolation(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that users are isolated per tenant."""
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

        # Act: Try to get user from different tenant
        response = client.get(
            f"/api/v1/users/{user2.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied (tenant mismatch)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "AUTH_TENANT_MISMATCH"

