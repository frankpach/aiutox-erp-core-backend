"""Integration tests for permission delegation functionality."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from sqlalchemy.orm import Session

from app.models.delegated_permission import DelegatedPermission
from app.models.module_role import ModuleRole
from app.models.user import User
from app.models.user_role import UserRole
from app.repositories.permission_repository import PermissionRepository
from app.services.permission_service import PermissionService


class TestPermissionDelegation:
    """Test suite for permission delegation functionality."""

    def test_leader_can_grant_permission_of_their_module(
        self, db_session: Session, test_user: User
    ):
        """Test that a leader can grant permission of their module."""
        # Arrange: Make user a manager of inventory module (has inventory.manage_users)
        module_role = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="manager",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        # Create target user
        from app.core.auth import hash_password
        from uuid import uuid4

        from app.models.tenant import Tenant

        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_user.tenant_id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        # Act: Grant permission
        permission_service = PermissionService(db_session)
        delegated_permission = permission_service.grant_permission(
            user_id=target_user.id,
            module="inventory",
            permission="inventory.edit",
            expires_at=None,
            granted_by=test_user.id,
        )

        # Assert: Permission was created
        assert delegated_permission is not None
        assert delegated_permission.user_id == target_user.id
        assert delegated_permission.granted_by == test_user.id
        assert delegated_permission.module == "inventory"
        assert delegated_permission.permission == "inventory.edit"
        assert delegated_permission.revoked_at is None
        assert delegated_permission.is_active is True

    def test_leader_cannot_grant_without_manage_users(
        self, db_session: Session, test_user: User
    ):
        """Test that a leader cannot grant permission without {module}.manage_users."""
        # Arrange: User has editor role (no manage_users permission)
        module_role = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        # Create target user
        from app.core.auth import hash_password
        from uuid import uuid4

        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_user.tenant_id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        # Act & Assert: Should raise HTTPException
        permission_service = PermissionService(db_session)
        with pytest.raises(Exception) as exc_info:
            permission_service.grant_permission(
                user_id=target_user.id,
                module="inventory",
                permission="inventory.edit",
                expires_at=None,
                granted_by=test_user.id,
            )
        assert "PERMISSION_DENIED" in str(exc_info.value) or "403" in str(exc_info.value)

    def test_leader_cannot_grant_manage_users_permission(
        self, db_session: Session, test_user: User
    ):
        """Test that a leader cannot grant *.manage_users permission."""
        # Arrange: Make user a manager
        module_role = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="manager",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        # Create target user
        from app.core.auth import hash_password
        from uuid import uuid4

        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_user.tenant_id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        # Act & Assert: Should raise HTTPException
        permission_service = PermissionService(db_session)
        with pytest.raises(Exception) as exc_info:
            permission_service.grant_permission(
                user_id=target_user.id,
                module="inventory",
                permission="inventory.manage_users",
                expires_at=None,
                granted_by=test_user.id,
            )
        assert "INVALID_PERMISSION" in str(exc_info.value) or "400" in str(exc_info.value)

    def test_leader_cannot_grant_global_permissions(
        self, db_session: Session, test_user: User
    ):
        """Test that a leader cannot grant global permissions (auth.*, system.*)."""
        # Arrange: Make user a manager
        module_role = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="manager",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        # Create target user
        from app.core.auth import hash_password
        from uuid import uuid4

        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_user.tenant_id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        permission_service = PermissionService(db_session)

        # Test auth.* permission
        with pytest.raises(Exception) as exc_info:
            permission_service.grant_permission(
                user_id=target_user.id,
                module="inventory",
                permission="auth.manage_users",
                expires_at=None,
                granted_by=test_user.id,
            )
        assert "INVALID_PERMISSION" in str(exc_info.value) or "400" in str(exc_info.value)

        # Test system.* permission
        with pytest.raises(Exception) as exc_info:
            permission_service.grant_permission(
                user_id=target_user.id,
                module="inventory",
                permission="system.configure",
                expires_at=None,
                granted_by=test_user.id,
            )
        assert "INVALID_PERMISSION" in str(exc_info.value) or "400" in str(exc_info.value)

    def test_leader_cannot_grant_permission_of_other_module(
        self, db_session: Session, test_user: User
    ):
        """Test that a leader cannot grant permission of another module."""
        # Arrange: Make user a manager of inventory module
        module_role = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="manager",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        # Create target user
        from app.core.auth import hash_password
        from uuid import uuid4

        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_user.tenant_id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        # Act & Assert: Should raise HTTPException
        permission_service = PermissionService(db_session)
        with pytest.raises(Exception) as exc_info:
            permission_service.grant_permission(
                user_id=target_user.id,
                module="inventory",
                permission="products.edit",  # Wrong module
                expires_at=None,
                granted_by=test_user.id,
            )
        assert "INVALID_PERMISSION" in str(exc_info.value) or "400" in str(exc_info.value)

    def test_permission_with_expiration_is_created_correctly(
        self, db_session: Session, test_user: User
    ):
        """Test that permission with expiration is created correctly."""
        # Arrange: Make user a manager
        module_role = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="manager",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        # Create target user
        from app.core.auth import hash_password
        from uuid import uuid4

        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_user.tenant_id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        # Act: Grant permission with expiration
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        permission_service = PermissionService(db_session)
        delegated_permission = permission_service.grant_permission(
            user_id=target_user.id,
            module="inventory",
            permission="inventory.edit",
            expires_at=expires_at,
            granted_by=test_user.id,
        )

        # Assert: Permission has expiration
        assert delegated_permission.expires_at == expires_at
        assert delegated_permission.is_active is True

    def test_permission_without_expiration_is_created_correctly(
        self, db_session: Session, test_user: User
    ):
        """Test that permission without expiration is created correctly."""
        # Arrange: Make user a manager
        module_role = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="manager",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        # Create target user
        from app.core.auth import hash_password
        from uuid import uuid4

        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_user.tenant_id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        # Act: Grant permission without expiration
        permission_service = PermissionService(db_session)
        delegated_permission = permission_service.grant_permission(
            user_id=target_user.id,
            module="inventory",
            permission="inventory.edit",
            expires_at=None,
            granted_by=test_user.id,
        )

        # Assert: Permission has no expiration
        assert delegated_permission.expires_at is None
        assert delegated_permission.is_active is True

    def test_leader_can_revoke_permission_they_granted(
        self, db_session: Session, test_user: User
    ):
        """Test that a leader can revoke permission they granted."""
        # Arrange: Make user a manager and grant permission
        module_role = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="manager",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        # Create target user
        from app.core.auth import hash_password
        from uuid import uuid4

        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_user.tenant_id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        permission_service = PermissionService(db_session)
        delegated_permission = permission_service.grant_permission(
            user_id=target_user.id,
            module="inventory",
            permission="inventory.edit",
            expires_at=None,
            granted_by=test_user.id,
        )

        # Act: Revoke permission
        permission_service.revoke_permission(delegated_permission.id, test_user.id)

        # Assert: Permission is revoked
        db_session.refresh(delegated_permission)
        assert delegated_permission.revoked_at is not None
        assert delegated_permission.is_active is False

    def test_leader_cannot_revoke_permission_granted_by_other(
        self, db_session: Session, test_user: User
    ):
        """Test that a leader cannot revoke permission granted by another leader."""
        # Arrange: Create two managers
        module_role1 = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="manager",
            granted_by=test_user.id,
        )
        db_session.add(module_role1)

        from app.core.auth import hash_password
        from uuid import uuid4

        leader2 = User(
            email=f"leader2-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Leader 2",
            tenant_id=test_user.tenant_id,
            is_active=True,
        )
        db_session.add(leader2)
        db_session.commit()

        module_role2 = ModuleRole(
            user_id=leader2.id,
            module="inventory",
            role_name="manager",
            granted_by=leader2.id,
        )
        db_session.add(module_role2)
        db_session.commit()

        # Create target user
        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_user.tenant_id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        # Leader2 grants permission
        permission_service = PermissionService(db_session)
        delegated_permission = permission_service.grant_permission(
            user_id=target_user.id,
            module="inventory",
            permission="inventory.edit",
            expires_at=None,
            granted_by=leader2.id,
        )

        # Act & Assert: test_user cannot revoke leader2's permission
        with pytest.raises(Exception) as exc_info:
            permission_service.revoke_permission(delegated_permission.id, test_user.id)
        assert "PERMISSION_DENIED" in str(exc_info.value) or "403" in str(exc_info.value)

    def test_admin_can_revoke_any_permission(
        self, db_session: Session, test_user: User
    ):
        """Test that admin can revoke any permission."""
        # Arrange: Make test_user an admin
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)

        # Create leader and target user
        from app.core.auth import hash_password
        from uuid import uuid4

        leader = User(
            email=f"leader-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Leader",
            tenant_id=test_user.tenant_id,
            is_active=True,
        )
        db_session.add(leader)
        db_session.commit()
        db_session.refresh(leader)

        module_role = ModuleRole(
            user_id=leader.id,
            module="inventory",
            role_name="manager",
            granted_by=leader.id,
        )
        db_session.add(module_role)

        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_user.tenant_id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        # Leader grants permission
        permission_service = PermissionService(db_session)
        delegated_permission = permission_service.grant_permission(
            user_id=target_user.id,
            module="inventory",
            permission="inventory.edit",
            expires_at=None,
            granted_by=leader.id,
        )

        # Act: Admin revokes permission
        permission_service.revoke_permission(delegated_permission.id, test_user.id)

        # Assert: Permission is revoked
        db_session.refresh(delegated_permission)
        assert delegated_permission.revoked_at is not None
        assert delegated_permission.is_active is False

    def test_admin_can_revoke_all_user_permissions(
        self, db_session: Session, test_user: User
    ):
        """Test that admin can revoke all permissions of a user."""
        # Arrange: Make test_user an admin
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)

        # Create leader and target user
        from app.core.auth import hash_password
        from uuid import uuid4

        leader = User(
            email=f"leader-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Leader",
            tenant_id=test_user.tenant_id,
            is_active=True,
        )
        db_session.add(leader)
        db_session.commit()
        db_session.refresh(leader)

        module_role = ModuleRole(
            user_id=leader.id,
            module="inventory",
            role_name="manager",
            granted_by=leader.id,
        )
        db_session.add(module_role)

        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_user.tenant_id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        # Leader grants multiple permissions
        permission_service = PermissionService(db_session)
        perm1 = permission_service.grant_permission(
            user_id=target_user.id,
            module="inventory",
            permission="inventory.edit",
            expires_at=None,
            granted_by=leader.id,
        )
        perm2 = permission_service.grant_permission(
            user_id=target_user.id,
            module="inventory",
            permission="inventory.view",
            expires_at=None,
            granted_by=leader.id,
        )

        # Act: Admin revokes all permissions
        revoked_count = permission_service.revoke_all_user_permissions(
            target_user.id, test_user.id
        )

        # Assert: Both permissions are revoked
        assert revoked_count == 2
        db_session.refresh(perm1)
        db_session.refresh(perm2)
        assert perm1.revoked_at is not None
        assert perm2.revoked_at is not None

    def test_revoked_permission_not_in_active_list(
        self, db_session: Session, test_user: User
    ):
        """Test that revoked permission is not in active permissions list."""
        # Arrange: Make user a manager and grant permission
        module_role = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="manager",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        # Create target user
        from app.core.auth import hash_password
        from uuid import uuid4

        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_user.tenant_id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        permission_service = PermissionService(db_session)
        delegated_permission = permission_service.grant_permission(
            user_id=target_user.id,
            module="inventory",
            permission="inventory.edit",
            expires_at=None,
            granted_by=test_user.id,
        )

        # Act: Revoke permission
        permission_service.revoke_permission(delegated_permission.id, test_user.id)

        # Assert: Permission is not in active list
        active_permissions = permission_service.get_user_delegated_permissions(
            target_user.id
        )
        assert len(active_permissions) == 0

    def test_delegated_permissions_included_in_effective_permissions(
        self, db_session: Session, test_user: User
    ):
        """Test that delegated permissions are included in effective permissions."""
        # Arrange: Make user a manager and grant permission
        module_role = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="manager",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        # Create target user
        from app.core.auth import hash_password
        from uuid import uuid4

        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_user.tenant_id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        permission_service = PermissionService(db_session)
        permission_service.grant_permission(
            user_id=target_user.id,
            module="inventory",
            permission="inventory.edit",
            expires_at=None,
            granted_by=test_user.id,
        )

        # Act: Get effective permissions
        effective_permissions = permission_service.get_effective_permissions(
            target_user.id
        )

        # Assert: Delegated permission is included
        assert "inventory.edit" in effective_permissions

    def test_expired_permission_not_in_effective_permissions(
        self, db_session: Session, test_user: User
    ):
        """Test that expired permission is not included in effective permissions."""
        # Arrange: Make user a manager
        module_role = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="manager",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        # Create target user
        from app.core.auth import hash_password
        from uuid import uuid4

        target_user = User(
            email=f"target-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Target User",
            tenant_id=test_user.tenant_id,
            is_active=True,
        )
        db_session.add(target_user)
        db_session.commit()

        # Grant permission with expiration in the past
        expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        permission_service = PermissionService(db_session)
        repo = PermissionRepository(db_session)
        expired_permission = repo.create_delegated_permission(
            user_id=target_user.id,
            granted_by=test_user.id,
            module="inventory",
            permission="inventory.edit",
            expires_at=expires_at,
        )

        # Act: Get effective permissions
        effective_permissions = permission_service.get_effective_permissions(
            target_user.id
        )

        # Assert: Expired permission is not included
        assert "inventory.edit" not in effective_permissions
        assert expired_permission.is_active is False

    def test_union_of_roles_module_roles_and_delegated_permissions(
        self, db_session: Session, test_user: User
    ):
        """Test that effective permissions are union of roles, module roles, and delegated."""
        # Arrange: Assign global role, module role (manager to grant permissions), and delegated permission
        global_role = UserRole(
            user_id=test_user.id,
            role="viewer",
            granted_by=test_user.id,
        )
        module_role = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="manager",  # Manager has inventory.manage_users
            granted_by=test_user.id,
        )
        db_session.add(global_role)
        db_session.add(module_role)
        db_session.commit()

        # Grant delegated permission
        permission_service = PermissionService(db_session)
        permission_service.grant_permission(
            user_id=test_user.id,
            module="inventory",
            permission="inventory.edit",
            expires_at=None,
            granted_by=test_user.id,
        )

        # Act: Get effective permissions
        effective_permissions = permission_service.get_effective_permissions(
            test_user.id
        )

        # Assert: Should have permissions from all sources
        # From viewer global role
        assert "*.*.view" in effective_permissions
        assert "system.view_reports" in effective_permissions
        # From inventory.manager module role
        assert "inventory.view" in effective_permissions
        assert "inventory.edit" in effective_permissions
        assert "inventory.adjust_stock" in effective_permissions
        assert "inventory.manage_users" in effective_permissions
        # From delegated permission (should still be there, but already included from manager role)
        assert "inventory.edit" in effective_permissions

