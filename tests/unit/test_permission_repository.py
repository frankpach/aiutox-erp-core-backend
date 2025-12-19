"""Unit tests for PermissionRepository."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.repositories.permission_repository import PermissionRepository


class TestPermissionRepository:
    """Test suite for PermissionRepository."""

    def test_create_delegated_permission(self, db_session, test_user):
        """Test creating a delegated permission."""
        repo = PermissionRepository(db_session)
        permission = repo.create_delegated_permission(
            user_id=test_user.id,
            granted_by=test_user.id,
            module="inventory",
            permission="inventory.edit",
            expires_at=None,
        )

        assert permission.id is not None
        assert permission.user_id == test_user.id
        assert permission.granted_by == test_user.id
        assert permission.module == "inventory"
        assert permission.permission == "inventory.edit"
        assert permission.expires_at is None
        assert permission.revoked_at is None
        assert permission.is_active is True

    def test_create_delegated_permission_with_expiration(self, db_session, test_user):
        """Test creating a delegated permission with expiration date."""
        repo = PermissionRepository(db_session)
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        permission = repo.create_delegated_permission(
            user_id=test_user.id,
            granted_by=test_user.id,
            module="products",
            permission="products.view",
            expires_at=expires_at,
        )

        assert permission.expires_at == expires_at
        assert permission.is_active is True

    def test_get_active_delegated_permissions(self, db_session, test_user):
        """Test getting active delegated permissions for a user."""
        repo = PermissionRepository(db_session)

        # Create active permission
        active_permission = repo.create_delegated_permission(
            user_id=test_user.id,
            granted_by=test_user.id,
            module="inventory",
            permission="inventory.edit",
        )

        # Create expired permission
        expired_at = datetime.now(timezone.utc) - timedelta(days=1)
        expired_permission = repo.create_delegated_permission(
            user_id=test_user.id,
            granted_by=test_user.id,
            module="inventory",
            permission="inventory.view",
            expires_at=expired_at,
        )

        # Create revoked permission
        revoked_permission = repo.create_delegated_permission(
            user_id=test_user.id,
            granted_by=test_user.id,
            module="products",
            permission="products.edit",
        )
        repo.revoke_permission(revoked_permission.id, test_user.id)

        # Get active permissions
        active_permissions = repo.get_active_delegated_permissions(test_user.id)

        # Should only return the active permission
        assert len(active_permissions) == 1
        assert active_permissions[0].id == active_permission.id
        assert active_permissions[0].is_active is True

    def test_get_active_delegated_permissions_excludes_expired(self, db_session, test_user):
        """Test that expired permissions are excluded from active permissions."""
        repo = PermissionRepository(db_session)

        # Create expired permission
        expired_at = datetime.now(timezone.utc) - timedelta(hours=1)
        repo.create_delegated_permission(
            user_id=test_user.id,
            granted_by=test_user.id,
            module="inventory",
            permission="inventory.view",
            expires_at=expired_at,
        )

        active_permissions = repo.get_active_delegated_permissions(test_user.id)
        assert len(active_permissions) == 0

    def test_get_active_delegated_permissions_excludes_revoked(self, db_session, test_user):
        """Test that revoked permissions are excluded from active permissions."""
        repo = PermissionRepository(db_session)

        # Create and revoke permission
        permission = repo.create_delegated_permission(
            user_id=test_user.id,
            granted_by=test_user.id,
            module="inventory",
            permission="inventory.edit",
        )
        repo.revoke_permission(permission.id, test_user.id)

        active_permissions = repo.get_active_delegated_permissions(test_user.id)
        assert len(active_permissions) == 0

    def test_get_delegated_permission_by_id(self, db_session, test_user):
        """Test getting a delegated permission by ID."""
        repo = PermissionRepository(db_session)
        permission = repo.create_delegated_permission(
            user_id=test_user.id,
            granted_by=test_user.id,
            module="inventory",
            permission="inventory.edit",
        )

        found_permission = repo.get_delegated_permission_by_id(permission.id)

        assert found_permission is not None
        assert found_permission.id == permission.id
        assert found_permission.permission == "inventory.edit"

    def test_get_delegated_permission_by_id_not_found(self, db_session):
        """Test getting a non-existent delegated permission by ID."""
        repo = PermissionRepository(db_session)
        non_existent_id = uuid4()
        permission = repo.get_delegated_permission_by_id(non_existent_id)

        assert permission is None

    def test_get_user_module_permissions(self, db_session, test_user):
        """Test getting all permissions for a user in a specific module."""
        repo = PermissionRepository(db_session)

        # Create permissions in different modules
        inventory_permission1 = repo.create_delegated_permission(
            user_id=test_user.id,
            granted_by=test_user.id,
            module="inventory",
            permission="inventory.edit",
        )
        inventory_permission2 = repo.create_delegated_permission(
            user_id=test_user.id,
            granted_by=test_user.id,
            module="inventory",
            permission="inventory.view",
        )
        products_permission = repo.create_delegated_permission(
            user_id=test_user.id,
            granted_by=test_user.id,
            module="products",
            permission="products.edit",
        )

        # Get inventory permissions
        inventory_permissions = repo.get_user_module_permissions(test_user.id, "inventory")

        assert len(inventory_permissions) == 2
        permission_ids = {p.id for p in inventory_permissions}
        assert inventory_permission1.id in permission_ids
        assert inventory_permission2.id in permission_ids
        assert products_permission.id not in permission_ids

    def test_revoke_permission(self, db_session, test_user):
        """Test revoking a delegated permission."""
        repo = PermissionRepository(db_session)
        permission = repo.create_delegated_permission(
            user_id=test_user.id,
            granted_by=test_user.id,
            module="inventory",
            permission="inventory.edit",
        )

        result = repo.revoke_permission(permission.id, test_user.id)

        assert result is True
        revoked_permission = repo.get_delegated_permission_by_id(permission.id)
        assert revoked_permission is not None
        assert revoked_permission.revoked_at is not None
        assert revoked_permission.is_active is False

    def test_revoke_permission_not_found(self, db_session, test_user):
        """Test revoking a non-existent permission."""
        repo = PermissionRepository(db_session)
        non_existent_id = uuid4()

        result = repo.revoke_permission(non_existent_id, test_user.id)

        assert result is False

    def test_revoke_permission_already_revoked(self, db_session, test_user):
        """Test revoking an already revoked permission."""
        repo = PermissionRepository(db_session)
        permission = repo.create_delegated_permission(
            user_id=test_user.id,
            granted_by=test_user.id,
            module="inventory",
            permission="inventory.edit",
        )
        repo.revoke_permission(permission.id, test_user.id)

        # Try to revoke again
        result = repo.revoke_permission(permission.id, test_user.id)

        assert result is False

    def test_revoke_all_user_permissions(self, db_session, test_user):
        """Test revoking all permissions for a user."""
        repo = PermissionRepository(db_session)

        # Create multiple permissions
        permission1 = repo.create_delegated_permission(
            user_id=test_user.id,
            granted_by=test_user.id,
            module="inventory",
            permission="inventory.edit",
        )
        permission2 = repo.create_delegated_permission(
            user_id=test_user.id,
            granted_by=test_user.id,
            module="products",
            permission="products.view",
        )

        # Revoke all
        count = repo.revoke_all_user_permissions(test_user.id, test_user.id)

        assert count == 2
        revoked_permission1 = repo.get_delegated_permission_by_id(permission1.id)
        revoked_permission2 = repo.get_delegated_permission_by_id(permission2.id)
        assert revoked_permission1.revoked_at is not None
        assert revoked_permission2.revoked_at is not None

    def test_revoke_all_user_permissions_none_exist(self, db_session, test_user):
        """Test revoking all permissions when user has none."""
        repo = PermissionRepository(db_session)

        count = repo.revoke_all_user_permissions(test_user.id, test_user.id)

        assert count == 0

    def test_get_permissions_by_granted_by(self, db_session, test_user):
        """Test getting permissions granted by a specific user."""
        repo = PermissionRepository(db_session)
        from app.models.user import User
        from app.core.auth.password import hash_password

        # Create another user
        other_user = User(
            email=f"other-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password"),
            tenant_id=test_user.tenant_id,
            is_active=True,
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        # Create permissions granted by test_user
        permission1 = repo.create_delegated_permission(
            user_id=other_user.id,
            granted_by=test_user.id,
            module="inventory",
            permission="inventory.edit",
        )
        permission2 = repo.create_delegated_permission(
            user_id=other_user.id,
            granted_by=test_user.id,
            module="products",
            permission="products.view",
        )

        # Create permission granted by other_user
        repo.create_delegated_permission(
            user_id=test_user.id,
            granted_by=other_user.id,
            module="inventory",
            permission="inventory.view",
        )

        # Get permissions granted by test_user
        granted_permissions = repo.get_permissions_by_granted_by(test_user.id)

        assert len(granted_permissions) == 2
        permission_ids = {p.id for p in granted_permissions}
        assert permission1.id in permission_ids
        assert permission2.id in permission_ids













