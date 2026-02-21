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
        # Arrange: User without config permission
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to list modules
        response = client_with_db.get(
            "/api/v1/config/modules",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"

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
        if response.status_code != status.HTTP_200_OK:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        assert "meta" in data

    def test_list_modules_returns_standard_format(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that GET /api/v1/config/modules returns StandardListResponse format."""
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

        # Assert: Should return StandardListResponse format
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "data" in data
        assert isinstance(data["data"], list)
        assert "meta" in data
        assert "total" in data["meta"]
        assert "page" in data["meta"]
        assert "page_size" in data["meta"]

    def test_get_module_info_requires_permission(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that getting module info requires config.view permission."""
        # Arrange: User without config permission
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to get module info
        response = client_with_db.get(
            "/api/v1/config/modules/products",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"

    def test_get_module_info_with_permission(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that user with config.view can get module info."""
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

        # Use first available module
        module_id = modules[0]["id"]

        # Act: Get module info
        response = client_with_db.get(
            f"/api/v1/config/modules/{module_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["id"] == module_id
        assert "name" in data["data"]
        assert "enabled" in data["data"]

    def test_enable_module_requires_permission(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that enabling a module requires config.edit permission."""
        # Arrange: User without config.edit permission
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to enable module
        response = client_with_db.put(
            "/api/v1/config/modules/products/enable",
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

        # Use first available module
        module_id = modules[0]["id"]

        # Act: Enable module
        response = client_with_db.put(
            f"/api/v1/config/modules/{module_id}/enable",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["enabled"] is True

    def test_disable_module_requires_permission(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that disabling a module requires config.edit permission."""
        # Arrange: User without config.edit permission
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to disable module
        response = client_with_db.put(
            "/api/v1/config/modules/products/disable",
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

        # Find a module that can be disabled (not core critical and no dependencies)
        module_id = None
        for module in modules:
            mid = module["id"]
            # Skip core critical modules
            if mid in ["auth", "users"]:
                continue
            # Skip modules with dependencies
            if module.get("dependencies"):
                continue
            # Found a suitable module
            module_id = mid
            break

        # Skip test if no suitable module found
        if not module_id:
            pytest.skip("No modules available that can be disabled")

        # Act: Disable module
        response = client_with_db.put(
            f"/api/v1/config/modules/{module_id}/disable",
            headers={"Authorization": f"Bearer {access_token}"},
        )

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

        response = client_with_db.get(
            "/api/v1/config/modules",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        modules = response.json()["data"]
        assert isinstance(modules, list)

        for module in modules:
            navigation_items = module.get("navigation_items", [])
            settings_links = module.get("settings_links", [])

            for item in [*navigation_items, *settings_links]:
                assert isinstance(item.get("id"), str) and item["id"]
                assert isinstance(item.get("label"), str) and item["label"]
                assert isinstance(item.get("path"), str) and item["path"].startswith(
                    "/"
                )
                assert isinstance(item.get("order"), int)

                permission = item.get("permission")
                assert permission is None or (
                    isinstance(permission, str) and permission
                )

                icon = item.get("icon")
                assert icon is None or icon in MODULE_NAVIGATION_ICON_TOKENS

                requirement = item.get("requires_module_setting")
                if requirement is not None:
                    assert (
                        isinstance(requirement.get("module"), str)
                        and requirement["module"]
                    )
                    assert (
                        isinstance(requirement.get("key"), str) and requirement["key"]
                    )

    def test_prioritized_modules_publish_dynamic_navigation(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        """Test that prioritized modules publish main/settings dynamic navigation entries."""
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

        response = client_with_db.get(
            "/api/v1/config/modules",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        modules = response.json()["data"]
        if not modules:
            pytest.skip("No modules available in registry")
        modules_by_id = {module["id"]: module for module in modules}

        prioritized_modules = {
            "tasks",
            "products",
            "inventory",
            "crm",
            "integrations",
            "files",
            "config",
            "notifications",
        }

        for module_id in prioritized_modules:
            assert module_id in modules_by_id
            module_data = modules_by_id[module_id]
            navigation_count = len(module_data.get("navigation_items", []))
            settings_count = len(module_data.get("settings_links", []))
            assert navigation_count + settings_count > 0
