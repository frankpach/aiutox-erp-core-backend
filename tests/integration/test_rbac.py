"""Integration tests for RBAC (Role-Based Access Control) system."""

from uuid import uuid4

import pytest
from fastapi import APIRouter, Depends, status
from fastapi.testclient import TestClient

from app.core.auth.dependencies import (
    get_current_user,
    get_user_permissions,
    require_any_permission,
    require_permission,
    require_roles,
)
from app.core.auth.permissions import has_permission
from app.core.db.deps import get_db
from app.models.user import User
from app.models.user_role import UserRole
from app.services.permission_service import PermissionService

# Create test router for testing authorization dependencies
rbac_test_router = APIRouter()


@rbac_test_router.get("/test/permission/{permission}")
async def rbac_test_permission_endpoint(
    permission: str,
    current_user: User = Depends(get_current_user),
    user_permissions: set[str] = Depends(get_user_permissions),
):
    """Test endpoint that requires a specific permission."""
    from app.core.auth.permissions import has_permission
    from app.core.exceptions import raise_forbidden

    if not has_permission(user_permissions, permission):
        raise_forbidden(
            code="AUTH_INSUFFICIENT_PERMISSIONS",
            message="Insufficient permissions",
            details={"required_permission": permission},
        )
    return {"message": "Access granted", "permission": permission, "user_id": str(current_user.id)}


@rbac_test_router.get("/test/roles")
async def rbac_test_roles_endpoint(
    user: User = Depends(require_roles("admin", "owner")),
):
    """Test endpoint that requires admin or owner role."""
    return {"message": "Access granted", "user_id": str(user.id)}


@rbac_test_router.get("/test/any-permission")
async def rbac_test_any_permission_endpoint(
    user: User = Depends(require_any_permission("inventory.view", "products.view")),
):
    """Test endpoint that requires any of the specified permissions."""
    return {"message": "Access granted", "user_id": str(user.id)}


@pytest.fixture(autouse=True)
def setup_test_router():
    """Fixture to add test router to app before tests and clean up after."""
    from app.main import app

    # Check if router is already included
    router_included = any(
        route.path.startswith("/test/") for route in app.routes
    )

    if not router_included:
        app.include_router(rbac_test_router)

    yield

    # Cleanup: remove test routes (optional, as they don't interfere)
    # FastAPI allows multiple includes of same routes, so cleanup is optional


def test_user_with_admin_role_has_permissions(db_session, test_user):
    """Test that user with admin role has correct permissions."""
    # Assign admin role
    role = UserRole(
        user_id=test_user.id,
        role="admin",
        granted_by=test_user.id,
    )
    db_session.add(role)
    db_session.commit()

    # Get permissions
    permission_service = PermissionService(db_session)
    permissions = permission_service.get_effective_permissions(test_user.id)

    # Admin should have auth and system permissions
    assert "auth.manage_users" in permissions
    assert "auth.manage_roles" in permissions
    assert "system.configure" in permissions
    assert "system.view_reports" in permissions


def test_user_with_viewer_role_has_read_only_permissions(db_session, test_user):
    """Test that user with viewer role only has read permissions."""
    # Assign viewer role
    role = UserRole(
        user_id=test_user.id,
        role="viewer",
        granted_by=test_user.id,
    )
    db_session.add(role)
    db_session.commit()

    # Get permissions
    permission_service = PermissionService(db_session)
    permissions = permission_service.get_effective_permissions(test_user.id)

    # Viewer should have read permissions
    assert "system.view_reports" in permissions
    assert "*.*.view" in permissions

    # Viewer should NOT have write permissions
    assert "auth.manage_users" not in permissions
    assert "system.configure" not in permissions
    assert "*.*.edit" not in permissions


def test_user_with_multiple_roles_has_union_of_permissions(db_session, test_user):
    """Test that user with multiple roles has union of permissions."""
    # Assign admin and viewer roles
    admin_role = UserRole(
        user_id=test_user.id,
        role="admin",
        granted_by=test_user.id,
    )
    viewer_role = UserRole(
        user_id=test_user.id,
        role="viewer",
        granted_by=test_user.id,
    )
    db_session.add(admin_role)
    db_session.add(viewer_role)
    db_session.commit()

    # Get permissions
    permission_service = PermissionService(db_session)
    permissions = permission_service.get_effective_permissions(test_user.id)

    # Should have permissions from both roles
    assert "auth.manage_users" in permissions  # From admin
    assert "system.view_reports" in permissions  # From both
    assert "*.*.view" in permissions  # From viewer


def test_owner_role_has_all_permissions(db_session, test_user):
    """Test that owner role has wildcard permission (*)."""
    # Assign owner role
    role = UserRole(
        user_id=test_user.id,
        role="owner",
        granted_by=test_user.id,
    )
    db_session.add(role)
    db_session.commit()

    # Get permissions
    permission_service = PermissionService(db_session)
    permissions = permission_service.get_effective_permissions(test_user.id)

    # Owner should have wildcard permission
    assert "*" in permissions


def test_require_permission_allows_access_with_permission(client, db_session, test_user):
    """Test that require_permission allows access when user has permission."""
    # Arrange: Assign admin role (has auth.manage_users)
    role = UserRole(
        user_id=test_user.id,
        role="admin",
        granted_by=test_user.id,
    )
    db_session.add(role)
    db_session.commit()

    # Act: Login to get token

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": test_user._plain_password,  # type: ignore
        },
    )
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["data"]["access_token"]

    # Act: Try to access endpoint with required permission
    response = client.get(
        "/test/permission/auth.manage_users",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Assert: Should allow access
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["message"] == "Access granted"
    assert data["permission"] == "auth.manage_users"
    assert data["user_id"] == str(test_user.id)


def test_require_permission_denies_access_without_permission(
    client, db_session, test_user
):
    """Test that require_permission denies access when user lacks permission."""
    # Arrange: Assign viewer role (doesn't have auth.manage_users)
    role = UserRole(
        user_id=test_user.id,
        role="viewer",
        granted_by=test_user.id,
    )
    db_session.add(role)
    db_session.commit()

    # Act: Login and try to access endpoint without required permission
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": test_user._plain_password,  # type: ignore
        },
    )
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["data"]["access_token"]

    response = client.get(
        "/test/permission/auth.manage_users",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Assert: Should deny access with proper error format
    assert response.status_code == status.HTTP_403_FORBIDDEN
    data = response.json()
    # Verify error response format according to API contract
    assert "error" in data
    assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"
    assert data["error"]["message"] == "Insufficient permissions"
    assert "details" in data["error"]
    assert data["error"]["details"]["required_permission"] == "auth.manage_users"


def test_wildcard_matching_module_wildcard(db_session, test_user):
    """Test wildcard matching with module wildcard (inventory.*)."""
    from app.core.auth.permissions import has_permission

    # Assign admin role (has *.*.view, *.*.edit, etc.)
    role = UserRole(
        user_id=test_user.id,
        role="admin",
        granted_by=test_user.id,
    )
    db_session.add(role)
    db_session.commit()

    permission_service = PermissionService(db_session)
    permissions = permission_service.get_effective_permissions(test_user.id)

    # Admin has *.*.view, so should match inventory.view
    assert has_permission(permissions, "inventory.view")
    assert has_permission(permissions, "products.view")
    assert has_permission(permissions, "orders.view")


def test_wildcard_matching_action_wildcard(db_session, test_user):
    """Test wildcard matching with action wildcard (*.view)."""
    from app.core.auth.permissions import has_permission

    # Assign viewer role (has *.*.view)
    role = UserRole(
        user_id=test_user.id,
        role="viewer",
        granted_by=test_user.id,
    )
    db_session.add(role)
    db_session.commit()

    permission_service = PermissionService(db_session)
    permissions = permission_service.get_effective_permissions(test_user.id)

    # Viewer has *.*.view, so should match any module.view
    assert has_permission(permissions, "inventory.view")
    assert has_permission(permissions, "products.view")
    assert has_permission(permissions, "orders.view")


def test_wildcard_matching_total_wildcard(db_session, test_user):
    """Test wildcard matching with total wildcard (*)."""
    from app.core.auth.permissions import has_permission

    # Assign owner role (has *)
    role = UserRole(
        user_id=test_user.id,
        role="owner",
        granted_by=test_user.id,
    )
    db_session.add(role)
    db_session.commit()

    permission_service = PermissionService(db_session)
    permissions = permission_service.get_effective_permissions(test_user.id)

    # Owner has *, so should match any permission
    assert has_permission(permissions, "inventory.view")
    assert has_permission(permissions, "inventory.edit")
    assert has_permission(permissions, "auth.manage_users")
    assert has_permission(permissions, "any.module.permission")


def test_require_roles_allows_access_with_role(client, db_session, test_user):
    """Test that require_roles allows access when user has required role."""
    # Arrange: Assign admin role
    role = UserRole(
        user_id=test_user.id,
        role="admin",
        granted_by=test_user.id,
    )
    db_session.add(role)
    db_session.commit()

    # Act: Login and access endpoint
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": test_user._plain_password,  # type: ignore
        },
    )
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["data"]["access_token"]

    # Try to access endpoint with required role
    response = client.get(
        "/test/roles",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["message"] == "Access granted"
    assert data["user_id"] == str(test_user.id)


def test_require_roles_denies_access_without_role(client, db_session, test_user):
    """Test that require_roles denies access when user lacks required role."""
    # Arrange: Assign viewer role (not admin or owner)
    role = UserRole(
        user_id=test_user.id,
        role="viewer",
        granted_by=test_user.id,
    )
    db_session.add(role)
    db_session.commit()

    # Act: Login and try to access endpoint
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": test_user._plain_password,  # type: ignore
        },
    )
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["data"]["access_token"]

    # Try to access endpoint without required role
    response = client.get(
        "/test/roles",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    data = response.json()
    # Verify error response format according to API contract
    assert "error" in data
    assert data["error"]["code"] == "AUTH_INSUFFICIENT_ROLES"
    assert data["error"]["message"] == "Insufficient roles"
    assert "details" in data["error"]
    assert "required_roles" in data["error"]["details"]


def test_require_any_permission_allows_access_with_any_permission(
    client, db_session, test_user
):
    """Test that require_any_permission allows access with any of the permissions."""
    # Arrange: Assign viewer role (has *.*.view which matches inventory.view)
    role = UserRole(
        user_id=test_user.id,
        role="viewer",
        granted_by=test_user.id,
    )
    db_session.add(role)
    db_session.commit()

    # Act: Login and access endpoint
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": test_user._plain_password,  # type: ignore
        },
    )
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["data"]["access_token"]

    # Try to access endpoint (viewer has *.*.view which matches inventory.view)
    response = client.get(
        "/test/any-permission",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["message"] == "Access granted"
    assert data["user_id"] == str(test_user.id)


def test_require_any_permission_denies_access_without_any_permission(
    client, db_session, test_user
):
    """Test that require_any_permission denies access without any of the permissions."""
    # Arrange: Assign staff role (has minimal permissions, no inventory.view or products.view)
    role = UserRole(
        user_id=test_user.id,
        role="staff",
        granted_by=test_user.id,
    )
    db_session.add(role)
    db_session.commit()

    # Act: Login and try to access endpoint
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": test_user._plain_password,  # type: ignore
        },
    )
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["data"]["access_token"]

    # Try to access endpoint without any of the required permissions
    response = client.get(
        "/test/any-permission",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    data = response.json()
    # Verify error response format according to API contract
    assert "error" in data
    assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"
    assert data["error"]["message"] == "Insufficient permissions"
    assert "details" in data["error"]
    assert "required_permissions" in data["error"]["details"]


def test_rbac_multi_tenant_isolation(client, db_session, test_user, test_tenant):
    """Test that RBAC permissions are isolated per tenant."""
    from uuid import uuid4

    from app.models.tenant import Tenant
    from app.models.user import User
    from app.core.auth import hash_password

    # Create another tenant
    other_tenant = Tenant(
        name="Other Tenant",
        slug=f"other-tenant-{uuid4().hex[:8]}",
    )
    db_session.add(other_tenant)
    db_session.commit()
    db_session.refresh(other_tenant)

    # Create user in other tenant with admin role
    other_user = User(
        email=f"other-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("password123"),
        full_name="Other User",
        tenant_id=other_tenant.id,
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    # Assign admin role to other_user
    other_role = UserRole(
        user_id=other_user.id,
        role="admin",
        granted_by=other_user.id,
    )
    db_session.add(other_role)
    db_session.commit()

    # Assign viewer role to test_user (in different tenant)
    test_role = UserRole(
        user_id=test_user.id,
        role="viewer",
        granted_by=test_user.id,
    )
    db_session.add(test_role)
    db_session.commit()

    # Get permissions for test_user
    permission_service = PermissionService(db_session)
    test_user_permissions = permission_service.get_effective_permissions(test_user.id)
    other_user_permissions = permission_service.get_effective_permissions(other_user.id)

    # Permissions should be calculated correctly for each user
    assert "*.*.view" in test_user_permissions  # viewer has read access
    assert "auth.manage_users" in other_user_permissions  # admin has management

    # But test_user should NOT have admin permissions even though other_user does
    assert "auth.manage_users" not in test_user_permissions

