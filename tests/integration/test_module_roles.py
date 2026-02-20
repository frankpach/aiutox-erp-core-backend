"""Integration tests for module roles (internal roles)."""

from sqlalchemy.orm import Session

from app.models.module_role import ModuleRole
from app.models.user import User
from app.models.user_role import UserRole
from app.services.permission_service import PermissionService


class TestModuleRoles:
    """Test suite for module roles functionality."""

    def test_user_with_module_role_has_permissions(
        self, db_session: Session, test_user: User
    ):
        """Test that user with module role gets correct permissions."""
        # Arrange: Assign inventory.editor role
        module_role = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        # Act: Get effective permissions
        permission_service = PermissionService(db_session)
        permissions = permission_service.get_effective_permissions(test_user.id)

        # Assert: Should have inventory permissions from editor role
        assert "inventory.view" in permissions
        assert "inventory.edit" in permissions
        assert "inventory.adjust_stock" in permissions

    def test_user_with_multiple_module_roles_has_union_of_permissions(
        self, db_session: Session, test_user: User
    ):
        """Test that user with multiple module roles gets union of permissions."""
        # Arrange: Assign inventory.editor and products.viewer roles
        inventory_role = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="editor",
            granted_by=test_user.id,
        )
        products_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="viewer",
            granted_by=test_user.id,
        )
        db_session.add(inventory_role)
        db_session.add(products_role)
        db_session.commit()

        # Act: Get effective permissions
        permission_service = PermissionService(db_session)
        permissions = permission_service.get_effective_permissions(test_user.id)

        # Assert: Should have permissions from both roles
        assert "inventory.view" in permissions
        assert "inventory.edit" in permissions
        assert "inventory.adjust_stock" in permissions
        assert "products.view" in permissions
        # products.viewer doesn't have edit permission
        assert "products.edit" not in permissions

    def test_user_with_global_and_module_roles_has_combined_permissions(
        self, db_session: Session, test_user: User
    ):
        """Test that global roles and module roles are combined."""
        # Arrange: Assign viewer global role and inventory.editor module role
        global_role = UserRole(
            user_id=test_user.id,
            role="viewer",
            granted_by=test_user.id,
        )
        module_role = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(global_role)
        db_session.add(module_role)
        db_session.commit()

        # Act: Get effective permissions
        permission_service = PermissionService(db_session)
        permissions = permission_service.get_effective_permissions(test_user.id)

        # Assert: Should have permissions from both sources
        # From viewer global role: *.*.view, system.view_reports
        assert "*.*.view" in permissions
        assert "system.view_reports" in permissions
        # From inventory.editor module role
        assert "inventory.view" in permissions
        assert "inventory.edit" in permissions
        assert "inventory.adjust_stock" in permissions

    def test_get_user_module_roles_returns_correct_roles(
        self, db_session: Session, test_user: User
    ):
        """Test that get_user_module_roles returns correct module roles."""
        # Arrange: Assign multiple module roles
        inventory_role = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="editor",
            granted_by=test_user.id,
        )
        products_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="manager",
            granted_by=test_user.id,
        )
        db_session.add(inventory_role)
        db_session.add(products_role)
        db_session.commit()

        # Act: Get module roles
        permission_service = PermissionService(db_session)
        module_roles = permission_service.get_user_module_roles(test_user.id)

        # Assert: Should return both roles
        assert len(module_roles) == 2
        role_modules = {role.module for role in module_roles}
        assert "inventory" in role_modules
        assert "products" in role_modules

    def test_get_module_role_permissions_returns_correct_permissions(
        self, db_session: Session
    ):
        """Test that get_module_role_permissions returns correct permissions."""
        # Arrange
        permission_service = PermissionService(db_session)

        # Act & Assert: Test inventory.editor
        permissions = permission_service.get_module_role_permissions(
            "inventory", "editor"
        )
        assert "inventory.view" in permissions
        assert "inventory.edit" in permissions
        assert "inventory.adjust_stock" in permissions
        assert "inventory.manage_users" not in permissions  # Only manager has this

        # Act & Assert: Test inventory.manager
        manager_permissions = permission_service.get_module_role_permissions(
            "inventory", "manager"
        )
        assert "inventory.view" in manager_permissions
        assert "inventory.edit" in manager_permissions
        assert "inventory.adjust_stock" in manager_permissions
        assert "inventory.manage_users" in manager_permissions

        # Act & Assert: Test inventory.viewer
        viewer_permissions = permission_service.get_module_role_permissions(
            "inventory", "viewer"
        )
        assert "inventory.view" in viewer_permissions
        assert "inventory.edit" not in viewer_permissions

    def test_get_module_role_permissions_with_internal_prefix(
        self, db_session: Session
    ):
        """Test that get_module_role_permissions handles 'internal.' prefix."""
        # Arrange
        permission_service = PermissionService(db_session)

        # Act: Test with 'internal.' prefix
        permissions1 = permission_service.get_module_role_permissions(
            "inventory", "internal.editor"
        )
        # Act: Test without 'internal.' prefix
        permissions2 = permission_service.get_module_role_permissions(
            "inventory", "editor"
        )

        # Assert: Both should return same permissions
        assert permissions1 == permissions2
        assert "inventory.view" in permissions1
        assert "inventory.edit" in permissions1

    def test_get_module_role_permissions_unknown_module_returns_empty(
        self, db_session: Session
    ):
        """Test that unknown module returns empty permissions."""
        # Arrange
        permission_service = PermissionService(db_session)

        # Act
        permissions = permission_service.get_module_role_permissions(
            "unknown_module", "editor"
        )

        # Assert
        assert permissions == set()

    def test_get_module_role_permissions_unknown_role_returns_empty(
        self, db_session: Session
    ):
        """Test that unknown role returns empty permissions."""
        # Arrange
        permission_service = PermissionService(db_session)

        # Act
        permissions = permission_service.get_module_role_permissions(
            "inventory", "unknown_role"
        )

        # Assert
        assert permissions == set()

    def test_module_role_manager_has_manage_users_permission(
        self, db_session: Session, test_user: User
    ):
        """Test that module role manager has manage_users permission."""
        # Arrange: Assign inventory.manager role
        module_role = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="manager",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        # Act: Get effective permissions
        permission_service = PermissionService(db_session)
        permissions = permission_service.get_effective_permissions(test_user.id)

        # Assert: Should have manage_users permission
        assert "inventory.manage_users" in permissions

    def test_module_roles_multi_tenant_isolation(
        self, db_session: Session, test_tenant, test_user: User
    ):
        """Test that module roles are isolated per tenant."""
        from uuid import uuid4

        from app.models.tenant import Tenant

        # Arrange: Create second tenant and user
        tenant2 = Tenant(
            name="Test Tenant 2",
            slug=f"test-tenant-2-{uuid4().hex[:8]}",
        )
        db_session.add(tenant2)
        db_session.commit()

        from app.core.auth import hash_password

        user2 = User(
            email=f"test-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("test_password_123"),
            full_name="Test User 2",
            tenant_id=tenant2.id,
            is_active=True,
        )
        db_session.add(user2)
        db_session.commit()

        # Assign module role to user1
        role1 = ModuleRole(
            user_id=test_user.id,
            module="inventory",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(role1)
        db_session.commit()

        # Act: Get module roles for user2
        permission_service = PermissionService(db_session)
        module_roles_user2 = permission_service.get_user_module_roles(user2.id)

        # Assert: user2 should have no module roles
        assert len(module_roles_user2) == 0

        # Act: Get module roles for user1
        module_roles_user1 = permission_service.get_user_module_roles(test_user.id)

        # Assert: user1 should have the role
        assert len(module_roles_user1) == 1
        assert module_roles_user1[0].module == "inventory"
        assert module_roles_user1[0].role_name == "editor"

