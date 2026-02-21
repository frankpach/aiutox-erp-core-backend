"""Integration tests for module management endpoints."""

import pytest
from fastapi import status

from app.core.module_navigation_icons import MODULE_NAVIGATION_ICON_TOKENS
from app.models.module_role import ModuleRole
from app.services.auth_service import AuthService


class TestConfigModules:
    """Test suite for module management endpoints."""

    def test_list_modules_requires_permission(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that listing modules requires config.view permission."""
        # Act: Try to list modules without permission
        response = client_with_db.get("/api/v1/config/modules")

        # Assert: Should be denied
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_modules_with_permission(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that user with config.view can list modules."""
        # Arrange: Assign config.viewer role
        module_role = ModuleRole(
            user_id=test_user.id,
            module="config",
            role_name="viewer",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: List modules
        response = client_with_db.get(
            "/api/v1/config/modules",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

        # Verify module structure
        if data["data"]:
            module = data["data"][0]
            assert "id" in module
            assert "name" in module
            assert "type" in module
            assert "enabled" in module
            assert "dependencies" in module
            assert "description" in module
            assert "has_router" in module
            assert "model_count" in module

    def test_enable_module_without_permission(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that enabling module without config.edit permission is denied."""
        # Arrange: Assign only config.viewer role (not editor)
        module_role = ModuleRole(
            user_id=test_user.id,
            module="config",
            role_name="viewer",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to enable module
        response = client_with_db.put(
            "/api/v1/config/modules/auth/enable",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"

    def test_enable_module_with_permission(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that user with config.edit can enable a module."""
        # Arrange: Assign config.editor role
        module_role = ModuleRole(
            user_id=test_user.id,
            module="config",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Enable auth module (should be safe)
        response = client_with_db.put(
            "/api/v1/config/modules/auth/enable",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["enabled"] is True

    def test_disable_module_without_permission(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that disabling module without config.edit permission is denied."""
        # Arrange: Assign only config.viewer role (not editor)
        module_role = ModuleRole(
            user_id=test_user.id,
            module="config",
            role_name="viewer",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to disable module
        response = client_with_db.put(
            "/api/v1/config/modules/auth/disable",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"

    def test_disable_module_with_permission(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that user with config.edit can disable a module."""
        # Arrange: Assign config.editor role
        module_role = ModuleRole(
            user_id=test_user.id,
            module="config",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # First, list modules to get a valid module_id
        list_response = client_with_db.get(
            "/api/v1/config/modules",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert list_response.status_code == status.HTTP_200_OK
        modules = list_response.json()["data"]

        # Skip test if no modules available
        if not modules:
            pytest.skip("No modules available in registry")

        # Debug: Print all modules
        print("DEBUG: Available modules:")
        for module in modules:
            print(
                f"  - {module['id']}: type={module.get('type')}, dependencies={module.get('dependencies')}"
            )

        # Find a module that can be disabled (not core critical and no dependencies)
        module_id = None
        for module in modules:
            mid = module["id"]
            print(
                f"DEBUG: Checking module {mid}: type={module.get('type')}, dependencies={module.get('dependencies')}"
            )
            # Skip core critical modules
            if mid in ["auth", "users"]:
                print(f"DEBUG: Skipping core critical module {mid}")
                continue
            # Skip modules with dependencies
            if module.get("dependencies"):
                print(
                    f"DEBUG: Skipping module {mid} with dependencies: {module.get('dependencies')}"
                )
                continue
            # Found a suitable module
            module_id = mid
            print(f"DEBUG: Found suitable module: {mid}")
            break

        # Skip test if no suitable module found
        if not module_id:
            pytest.skip("No modules available that can be disabled")

        # Act: Disable module
        print(f"DEBUG: Attempting to disable module: {module_id}")
        response = client_with_db.put(
            f"/api/v1/config/modules/{module_id}/disable",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        print(f"DEBUG: Response status: {response.status_code}")
        if response.status_code != 200:
            print(f"DEBUG: Response body: {response.text}")

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["enabled"] is False

    def test_modules_expose_valid_navigation_items(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that modules expose navigation items with expected schema semantics."""
        module_role = ModuleRole(
            user_id=test_user.id,
            module="config",
            role_name="viewer",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Get modules
        response = client_with_db.get(
            "/api/v1/config/modules",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_200_OK

        modules = response.json()["data"]

        # Assert: All modules have valid navigation structure
        for module in modules:
            if module.get("navigation_items"):
                for nav_item in module["navigation_items"]:
                    # Check required fields
                    assert "title" in nav_item
                    assert "path" in nav_item
                    assert "icon" in nav_item

                    # Check icon is valid
                    assert nav_item["icon"] in MODULE_NAVIGATION_ICON_TOKENS
