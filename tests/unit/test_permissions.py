"""Unit tests for permission verification utilities."""


from app.core.auth.permissions import ROLE_PERMISSIONS, has_permission


def test_has_permission_exact_match():
    """Test that has_permission returns True for exact permission match."""
    user_permissions = {"inventory.view", "inventory.edit", "products.view"}

    assert has_permission(user_permissions, "inventory.view") is True
    assert has_permission(user_permissions, "inventory.edit") is True
    assert has_permission(user_permissions, "products.view") is True
    assert has_permission(user_permissions, "products.edit") is False


def test_has_permission_module_wildcard():
    """Test wildcard matching with module wildcard (inventory.*)."""
    user_permissions = {"inventory.*", "products.view"}

    # inventory.* should match all inventory permissions
    assert has_permission(user_permissions, "inventory.view") is True
    assert has_permission(user_permissions, "inventory.edit") is True
    assert has_permission(user_permissions, "inventory.delete") is True
    assert has_permission(user_permissions, "inventory.adjust_stock") is True

    # But not other modules
    assert has_permission(user_permissions, "products.edit") is False
    assert has_permission(user_permissions, "orders.view") is False


def test_has_permission_action_wildcard():
    """Test wildcard matching with action wildcard (*.view)."""
    user_permissions = {"*.view", "products.edit"}

    # *.view should match view permissions for all modules
    assert has_permission(user_permissions, "inventory.view") is True
    assert has_permission(user_permissions, "products.view") is True
    assert has_permission(user_permissions, "orders.view") is True
    assert has_permission(user_permissions, "auth.view") is True

    # But not other actions
    assert has_permission(user_permissions, "inventory.edit") is False
    assert has_permission(user_permissions, "products.delete") is False
    # products.edit is explicitly granted
    assert has_permission(user_permissions, "products.edit") is True


def test_has_permission_total_wildcard():
    """Test wildcard matching with total wildcard (* or *.*)."""
    # Test with *
    user_permissions_star = {"*"}
    assert has_permission(user_permissions_star, "inventory.view") is True
    assert has_permission(user_permissions_star, "inventory.edit") is True
    assert has_permission(user_permissions_star, "auth.manage_users") is True
    assert has_permission(user_permissions_star, "any.module.permission") is True

    # Test with *.*
    user_permissions_star_star = {"*.*"}
    assert has_permission(user_permissions_star_star, "inventory.view") is True
    assert has_permission(user_permissions_star_star, "inventory.edit") is True
    assert has_permission(user_permissions_star_star, "auth.manage_users") is True
    assert has_permission(user_permissions_star_star, "any.module.permission") is True


def test_has_permission_no_match():
    """Test that has_permission returns False when no match is found."""
    user_permissions = {"inventory.view", "products.edit"}

    assert has_permission(user_permissions, "inventory.edit") is False
    assert has_permission(user_permissions, "products.view") is False
    assert has_permission(user_permissions, "orders.view") is False
    assert has_permission(user_permissions, "auth.manage_users") is False


def test_has_permission_empty_set():
    """Test that has_permission returns False for empty permission set."""
    user_permissions = set()

    assert has_permission(user_permissions, "inventory.view") is False
    assert has_permission(user_permissions, "auth.manage_users") is False
    assert has_permission(user_permissions, "any.permission") is False


def test_has_permission_complex_wildcard_scenarios():
    """Test complex wildcard matching scenarios."""
    # Multiple wildcards
    user_permissions = {"inventory.*", "*.view", "products.edit"}

    # inventory.* should take precedence for inventory permissions
    assert has_permission(user_permissions, "inventory.view") is True
    assert has_permission(user_permissions, "inventory.edit") is True
    assert has_permission(user_permissions, "inventory.delete") is True

    # *.view should match other modules
    assert has_permission(user_permissions, "orders.view") is True
    assert has_permission(user_permissions, "auth.view") is True

    # Explicit permissions
    assert has_permission(user_permissions, "products.edit") is True

    # Not covered
    assert has_permission(user_permissions, "orders.edit") is False
    assert has_permission(user_permissions, "auth.manage_users") is False


def test_role_permissions_owner_has_wildcard():
    """Test that owner role has wildcard permission."""
    owner_permissions = ROLE_PERMISSIONS["owner"]
    assert "*" in owner_permissions


def test_role_permissions_admin_has_management_permissions():
    """Test that admin role has management permissions."""
    admin_permissions = ROLE_PERMISSIONS["admin"]
    assert "auth.manage_users" in admin_permissions
    assert "auth.manage_roles" in admin_permissions
    assert "system.configure" in admin_permissions
    assert "system.view_reports" in admin_permissions


def test_role_permissions_viewer_has_read_only():
    """Test that viewer role has read-only permissions."""
    viewer_permissions = ROLE_PERMISSIONS["viewer"]
    assert "system.view_reports" in viewer_permissions
    assert "*.*.view" in viewer_permissions
    assert "auth.manage_users" not in viewer_permissions
    assert "system.configure" not in viewer_permissions


def test_role_permissions_all_roles_defined():
    """Test that all expected roles are defined."""
    expected_roles = {"owner", "admin", "manager", "staff", "viewer"}
    defined_roles = set(ROLE_PERMISSIONS.keys())
    assert expected_roles == defined_roles


def test_has_permission_with_owner_role():
    """Test that owner role wildcard works correctly."""
    owner_permissions = ROLE_PERMISSIONS["owner"]
    assert has_permission(owner_permissions, "inventory.view") is True
    assert has_permission(owner_permissions, "auth.manage_users") is True
    assert has_permission(owner_permissions, "any.module.permission") is True


def test_has_permission_with_admin_role():
    """Test that admin role permissions work correctly."""
    admin_permissions = ROLE_PERMISSIONS["admin"]
    # Admin has *.*.view, so should match inventory.view
    assert has_permission(admin_permissions, "inventory.view") is True
    assert has_permission(admin_permissions, "products.view") is True
    # Admin has *.*.edit
    assert has_permission(admin_permissions, "inventory.edit") is True
    # Admin has explicit permissions
    assert has_permission(admin_permissions, "auth.manage_users") is True
    assert has_permission(admin_permissions, "system.configure") is True


def test_has_permission_with_viewer_role():
    """Test that viewer role permissions work correctly."""
    viewer_permissions = ROLE_PERMISSIONS["viewer"]
    # Viewer has *.*.view
    assert has_permission(viewer_permissions, "inventory.view") is True
    assert has_permission(viewer_permissions, "products.view") is True
    # Viewer should NOT have edit permissions
    assert has_permission(viewer_permissions, "inventory.edit") is False
    assert has_permission(viewer_permissions, "auth.manage_users") is False

