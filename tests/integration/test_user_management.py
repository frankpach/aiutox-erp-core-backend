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
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that listing users requires auth.manage_users permission."""
        # Arrange: User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to list users
        response = client_with_db.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"

    def test_list_users_with_permission(
        self, client_with_db, db_session, test_user, test_tenant
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
        response = client_with_db.get(
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
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that creating user requires auth.manage_users permission."""
        # Arrange: User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to create user
        response = client_with_db.post(
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
        self, client_with_db, db_session, test_user, test_tenant
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
        response = client_with_db.post(
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
        self, client_with_db, db_session, test_user, test_tenant
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
        response = client_with_db.post(
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
        assert "error" in data
        assert "USER_ALREADY_EXISTS" in data["error"]["code"]

    def test_get_user_requires_auth_manage_users(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that getting user requires auth.manage_users permission."""
        # Arrange: User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to get user
        response = client_with_db.get(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_user_with_permission(
        self, client_with_db, db_session, test_user, test_tenant
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
        response = client_with_db.get(
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
        self, client_with_db, db_session, test_user, test_tenant
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
        response = client_with_db.get(
            f"/api/v1/users/{fake_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return 404
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "USER_NOT_FOUND"

    def test_update_user_requires_auth_manage_users(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that updating user requires auth.manage_users permission."""
        # Arrange: User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to update user
        response = client_with_db.patch(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"full_name": "Updated Name"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_user_with_permission(
        self, client_with_db, db_session, test_user, test_tenant
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
        response = client_with_db.patch(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"full_name": "Updated Name"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["full_name"] == "Updated Name"

    def test_update_user_deactivate_revokes_tokens(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that updating user is_active to False revokes all tokens."""
        from app.repositories.refresh_token_repository import RefreshTokenRepository

        # Arrange: Create target user
        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()
        target_user_id = target_user.id

        # Create refresh tokens for target user
        auth_service = AuthService(db_session)
        refresh_token1 = auth_service.create_refresh_token_for_user(target_user)
        refresh_token2 = auth_service.create_refresh_token_for_user(target_user)

        # Verify tokens exist
        refresh_token_repo = RefreshTokenRepository(db_session)
        assert refresh_token_repo.find_valid_token(target_user_id, refresh_token1) is not None
        assert refresh_token_repo.find_valid_token(target_user_id, refresh_token2) is not None

        # Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Update user to inactive
        response = client_with_db.patch(
            f"/api/v1/users/{target_user_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"is_active": False},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["is_active"] is False

        # Verify user is inactive
        db_session.refresh(target_user)
        assert target_user.is_active is False

        # Verify all tokens are revoked
        assert refresh_token_repo.find_valid_token(target_user_id, refresh_token1) is None
        assert refresh_token_repo.find_valid_token(target_user_id, refresh_token2) is None

    def test_delete_user_requires_auth_manage_users(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that deleting user requires auth.manage_users permission."""
        # Arrange: User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to delete user
        response = client_with_db.delete(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_user_with_permission_soft_delete(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that admin can soft delete user (sets is_active=False and revokes tokens)."""
        from app.repositories.refresh_token_repository import RefreshTokenRepository

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
        target_user_id = target_user.id

        # Create refresh tokens for target user
        auth_service = AuthService(db_session)
        refresh_token1 = auth_service.create_refresh_token_for_user(target_user)
        refresh_token2 = auth_service.create_refresh_token_for_user(target_user)

        # Verify tokens exist
        refresh_token_repo = RefreshTokenRepository(db_session)
        assert refresh_token_repo.find_valid_token(target_user_id, refresh_token1) is not None
        assert refresh_token_repo.find_valid_token(target_user_id, refresh_token2) is not None

        # Assign admin role to test_user
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Delete user (soft delete)
        response = client_with_db.delete(
            f"/api/v1/users/{target_user_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "message" in data["data"]

        # Verify user is soft deleted (still exists but inactive)
        db_session.refresh(target_user)
        deleted_user = db_session.query(User).filter(User.id == target_user_id).first()
        assert deleted_user is not None
        assert deleted_user.is_active is False

        # Verify all tokens are revoked
        assert refresh_token_repo.find_valid_token(target_user_id, refresh_token1) is None
        assert refresh_token_repo.find_valid_token(target_user_id, refresh_token2) is None

    def test_list_users_pagination(
        self, client_with_db, db_session, test_user, test_tenant
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
        response = client_with_db.get(
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
        self, client_with_db, db_session, test_user, test_tenant
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
        response = client_with_db.get(
            f"/api/v1/users/{user2.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied (tenant mismatch)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTH_TENANT_MISMATCH"

    def test_list_users_with_search_filter(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test listing users with search filter."""
        # Arrange: Create users with different names
        user1 = User(
            email=f"john.doe-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            first_name="John",
            last_name="Doe",
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(user1)

        user2 = User(
            email=f"jane.smith-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            first_name="Jane",
            last_name="Smith",
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(user2)
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

        # Act: Search for "john"
        response = client_with_db.get(
            "/api/v1/users?search=john",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return only john
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        users = data["data"]
        assert len(users) >= 1
        assert any("john" in user["email"].lower() or "john" in (user.get("first_name") or "").lower() for user in users)

    def test_list_users_with_is_active_filter(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test listing users with is_active filter."""
        # Arrange: Create active and inactive users
        active_user = User(
            email=f"active-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Active User",
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(active_user)

        inactive_user = User(
            email=f"inactive-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Inactive User",
            tenant_id=test_tenant.id,
            is_active=False,
        )
        db_session.add(inactive_user)
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

        # Act: Filter active users
        response = client_with_db.get(
            "/api/v1/users?is_active=true",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return only active users
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        users = data["data"]
        assert all(user["is_active"] is True for user in users)

        # Act: Filter inactive users
        response = client_with_db.get(
            "/api/v1/users?is_active=false",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return only inactive users
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        users = data["data"]
        assert all(user["is_active"] is False for user in users)

    def test_bulk_action_activate(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test bulk activate action."""
        # Arrange: Create inactive users
        user1 = User(
            email=f"user1-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="User 1",
            tenant_id=test_tenant.id,
            is_active=False,
        )
        db_session.add(user1)

        user2 = User(
            email=f"user2-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="User 2",
            tenant_id=test_tenant.id,
            is_active=False,
        )
        db_session.add(user2)
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

        # Act: Bulk activate
        response = client_with_db.post(
            "/api/v1/users/bulk",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "action": "activate",
                "user_ids": [str(user1.id), str(user2.id)],
            },
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["action"] == "activate"
        assert data["data"]["success"] == 2
        assert data["data"]["failed"] == 0

        # Verify users are activated
        db_session.refresh(user1)
        db_session.refresh(user2)
        assert user1.is_active is True
        assert user2.is_active is True

    def test_bulk_action_deactivate(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test bulk deactivate action (soft delete with token revocation)."""
        from app.repositories.refresh_token_repository import RefreshTokenRepository

        # Arrange: Create active users
        user1 = User(
            email=f"user1-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="User 1",
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(user1)
        db_session.commit()
        user1_id = user1.id

        # Create refresh tokens for user1
        auth_service = AuthService(db_session)
        refresh_token1 = auth_service.create_refresh_token_for_user(user1)
        refresh_token2 = auth_service.create_refresh_token_for_user(user1)

        # Verify tokens exist
        refresh_token_repo = RefreshTokenRepository(db_session)
        assert refresh_token_repo.find_valid_token(user1_id, refresh_token1) is not None
        assert refresh_token_repo.find_valid_token(user1_id, refresh_token2) is not None

        # Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Bulk deactivate
        response = client_with_db.post(
            "/api/v1/users/bulk",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "action": "deactivate",
                "user_ids": [str(user1_id)],
            },
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["action"] == "deactivate"
        assert data["data"]["success"] == 1

        # Verify user is deactivated but still exists
        db_session.refresh(user1)
        assert user1.is_active is False
        assert db_session.query(User).filter(User.id == user1_id).first() is not None

        # Verify all tokens are revoked
        assert refresh_token_repo.find_valid_token(user1_id, refresh_token1) is None
        assert refresh_token_repo.find_valid_token(user1_id, refresh_token2) is None

    def test_bulk_action_delete(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test bulk delete action (soft delete with token revocation)."""
        from app.repositories.refresh_token_repository import RefreshTokenRepository

        # Arrange: Create users to delete
        user1 = User(
            email=f"user1-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="User 1",
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(user1)
        db_session.commit()
        user1_id = user1.id

        # Create refresh tokens for user1
        auth_service = AuthService(db_session)
        refresh_token1 = auth_service.create_refresh_token_for_user(user1)
        refresh_token2 = auth_service.create_refresh_token_for_user(user1)

        # Verify tokens exist
        refresh_token_repo = RefreshTokenRepository(db_session)
        assert refresh_token_repo.find_valid_token(user1_id, refresh_token1) is not None
        assert refresh_token_repo.find_valid_token(user1_id, refresh_token2) is not None

        # Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Bulk delete
        response = client_with_db.post(
            "/api/v1/users/bulk",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "action": "delete",
                "user_ids": [str(user1_id)],
            },
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["action"] == "delete"
        assert data["data"]["success"] == 1

        # Verify user is soft deleted (still exists but inactive)
        db_session.refresh(user1)
        deleted_user = db_session.query(User).filter(User.id == user1_id).first()
        assert deleted_user is not None
        assert deleted_user.is_active is False

        # Verify all tokens are revoked
        assert refresh_token_repo.find_valid_token(user1_id, refresh_token1) is None
        assert refresh_token_repo.find_valid_token(user1_id, refresh_token2) is None

    def test_bulk_action_tenant_isolation(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that bulk actions only affect users from the same tenant."""
        from app.models.tenant import Tenant

        # Arrange: Create user from different tenant
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

        # Act: Try to bulk delete user from different tenant
        response = client_with_db.post(
            "/api/v1/users/bulk",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "action": "delete",
                "user_ids": [str(user2.id)],
            },
        )

        # Assert: Should succeed but user should not be deleted
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        # Should fail because tenant mismatch
        assert data["data"]["success"] == 0
        assert data["data"]["failed"] == 1

        # Verify user still exists
        assert db_session.query(User).filter(User.id == user2.id).first() is not None

