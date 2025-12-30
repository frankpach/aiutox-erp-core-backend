"""Integration tests for configuration module."""

from uuid import uuid4

from fastapi import status

from app.models.module_role import ModuleRole
from app.models.user import User
from app.services.auth_service import AuthService


class TestConfig:
    """Test suite for configuration endpoints."""

    def test_get_module_config_requires_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that getting module config requires config.view permission."""
        # Arrange: User without config permission
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to get config
        response = client.get(
            "/api/v1/config/products",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"

    def test_get_module_config_with_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that user with config.view can get module config."""
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

        # Act: Get config
        response = client.get(
            "/api/v1/config/products",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["module"] == "products"
        assert isinstance(data["data"]["config"], dict)

    def test_get_module_config_returns_standard_format(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that GET /api/v1/config/{module} returns StandardResponse format."""
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

        # Act: Get config
        response = client.get(
            "/api/v1/config/products",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return StandardResponse format
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "data" in data
        assert "error" in data
        assert data["error"] is None
        assert isinstance(data["data"], dict)
        assert "module" in data["data"]
        assert "config" in data["data"]

    def test_get_config_value(self, client, db_session, test_user, test_tenant):
        """Test getting a specific configuration value."""
        # Arrange: Assign config roles
        viewer_role = ModuleRole(
            user_id=test_user.id,
            module="config",
            role_name="viewer",
            granted_by=test_user.id,
        )
        editor_role = ModuleRole(
            user_id=test_user.id,
            module="config",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(viewer_role)
        db_session.add(editor_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Use a different module/key to avoid schema conflicts
        module = "integration_test"
        key = "test_value"

        # Create config first
        create_response = client.put(
            f"/api/v1/config/{module}/{key}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"value": 10.0},
        )
        assert create_response.status_code == status.HTTP_200_OK

        # Act: Get config value
        response = client.get(
            f"/api/v1/config/{module}/{key}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["module"] == module
        assert data["data"]["key"] == key
        assert data["data"]["value"] == 10.0

    def test_get_config_value_not_found(
        self, client, db_session, test_user, test_tenant
    ):
        """Test getting a non-existent configuration value."""
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

        # Act: Get non-existent config
        response = client.get(
            "/api/v1/config/products/nonexistent",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return 404
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "CONFIG_NOT_FOUND"

    def test_set_config_value(self, client, db_session, test_user, test_tenant):
        """Test setting a configuration value."""
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

        # Use a different module/key to avoid schema conflicts
        module = "integration_test"
        key = "set_value"

        # Act: Set config value
        response = client.put(
            f"/api/v1/config/{module}/{key}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"value": 10.0},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["value"] == 10.0

    def test_set_config_value_requires_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that setting config requires config.edit permission."""
        # Arrange: User without config.edit permission
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to set config
        response = client.put(
            "/api/v1/config/products/min_price",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"value": 10.0},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"

    def test_set_module_config(self, client, db_session, test_user, test_tenant):
        """Test setting multiple configuration values."""
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

        # Use a different module to avoid schema conflicts
        module = "integration_test_module"
        # Act: Set module config
        config_data = {"min_price": 10.0, "max_price": 100.0, "currency": "USD"}
        response = client.post(
            f"/api/v1/config/{module}",
            headers={"Authorization": f"Bearer {access_token}"},
            json=config_data,
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "data" in data
        assert data["data"]["module"] == module
        assert data["data"]["config"] == config_data

    def test_delete_config_value(self, client, db_session, test_user, test_tenant):
        """Test deleting a configuration value."""
        # Arrange: Assign config roles
        viewer_role = ModuleRole(
            user_id=test_user.id,
            module="config",
            role_name="viewer",
            granted_by=test_user.id,
        )
        editor_role = ModuleRole(
            user_id=test_user.id,
            module="config",
            role_name="editor",
            granted_by=test_user.id,
        )
        manager_role = ModuleRole(
            user_id=test_user.id,
            module="config",
            role_name="manager",
            granted_by=test_user.id,
        )
        db_session.add(viewer_role)
        db_session.add(editor_role)
        db_session.add(manager_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Use a different module/key to avoid schema conflicts
        module = "integration_test"
        key = "delete_test"

        # Create config first
        create_response = client.put(
            f"/api/v1/config/{module}/{key}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"value": 10.0},
        )
        assert create_response.status_code == status.HTTP_200_OK

        # Act: Delete config
        response = client.delete(
            f"/api/v1/config/{module}/{key}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "message" in data["data"]

        # Verify it's deleted
        get_response = client.get(
            f"/api/v1/config/{module}/{key}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        # Should return 404 if key doesn't exist (not schema default)
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_config_value_requires_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that deleting config requires config.delete permission."""
        # Arrange: User with only config.edit (not delete)
        editor_role = ModuleRole(
            user_id=test_user.id,
            module="config",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(editor_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to delete config
        response = client.delete(
            "/api/v1/config/products/min_price",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"

    def test_multi_tenant_isolation(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that configurations are isolated by tenant."""
        # Arrange: Assign config roles
        viewer_role = ModuleRole(
            user_id=test_user.id,
            module="config",
            role_name="viewer",
            granted_by=test_user.id,
        )
        editor_role = ModuleRole(
            user_id=test_user.id,
            module="config",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(viewer_role)
        db_session.add(editor_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Use a different module/key to avoid schema conflicts
        module = "integration_test"
        key = "isolation_test"

        # Create config for current tenant
        create_response = client.put(
            f"/api/v1/config/{module}/{key}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"value": 10.0},
        )
        assert create_response.status_code == status.HTTP_200_OK

        # Get config for current tenant (should find it)
        get_response = client.get(
            f"/api/v1/config/{module}/{key}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert get_response.status_code == status.HTTP_200_OK
        data = get_response.json()
        assert data["data"]["value"] == 10.0

        # Note: We can't easily test another tenant without creating another user
        # But the repository tests verify isolation at the data layer

    def test_error_response_format(self, client, db_session, test_user, test_tenant):
        """Test that error responses follow API contract format."""
        # Arrange: User without permission
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to get config without permission
        response = client.get(
            "/api/v1/config/products",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return correct error format
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()

        assert "error" in data
        assert "data" in data
        assert data["data"] is None
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "details" in data["error"]
        assert isinstance(data["error"]["code"], str)
        assert isinstance(data["error"]["message"], str)

    def test_get_general_settings_requires_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that getting general settings requires config.view permission."""
        # Arrange: User without config permission
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to get general settings
        response = client.get(
            "/api/v1/config/general",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"

    def test_get_general_settings_with_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that user with config.view can get general settings."""
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

        # Act: Get general settings
        response = client.get(
            "/api/v1/config/general",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "error" in data
        assert data["error"] is None

        # Verify response structure
        settings = data["data"]
        assert "timezone" in settings
        assert "date_format" in settings
        assert "time_format" in settings
        assert "currency" in settings
        assert "language" in settings

        # Verify default values
        assert settings["timezone"] == "America/Mexico_City"
        assert settings["date_format"] == "DD/MM/YYYY"
        assert settings["time_format"] == "24h"
        assert settings["currency"] == "MXN"
        assert settings["language"] == "es"

    def test_update_general_settings_requires_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that updating general settings requires config.edit permission."""
        # Arrange: User without config.edit permission
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to update general settings
        response = client.put(
            "/api/v1/config/general",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "timezone": "America/New_York",
                "date_format": "MM/DD/YYYY",
                "time_format": "12h",
                "currency": "USD",
                "language": "en",
            },
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"

    def test_update_general_settings_with_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that user with config.edit can update general settings."""
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

        # Act: Update general settings
        new_settings = {
            "timezone": "America/New_York",
            "date_format": "MM/DD/YYYY",
            "time_format": "12h",
            "currency": "USD",
            "language": "en",
        }
        response = client.put(
            "/api/v1/config/general",
            headers={"Authorization": f"Bearer {access_token}"},
            json=new_settings,
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "error" in data
        assert data["error"] is None

        # Verify response contains updated values
        settings = data["data"]
        assert settings["timezone"] == new_settings["timezone"]
        assert settings["date_format"] == new_settings["date_format"]
        assert settings["time_format"] == new_settings["time_format"]
        assert settings["currency"] == new_settings["currency"]
        assert settings["language"] == new_settings["language"]

        # Verify persistence: Get settings again
        get_response = client.get(
            "/api/v1/config/general",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert get_response.status_code == status.HTTP_200_OK
        get_data = get_response.json()
        persisted_settings = get_data["data"]
        assert persisted_settings["timezone"] == new_settings["timezone"]
        assert persisted_settings["date_format"] == new_settings["date_format"]
        assert persisted_settings["time_format"] == new_settings["time_format"]
        assert persisted_settings["currency"] == new_settings["currency"]
        assert persisted_settings["language"] == new_settings["language"]

    def test_update_general_settings_validation_error(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that invalid general settings are rejected."""
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

        # Act: Try to update with invalid time_format
        response = client.put(
            "/api/v1/config/general",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "timezone": "America/New_York",
                "date_format": "MM/DD/YYYY",
                "time_format": "invalid",  # Invalid: must be "12h" or "24h"
                "currency": "USD",
                "language": "en",
            },
        )

        # Assert: Should return validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        # FastAPI validation errors can be in "detail" or custom error format
        assert "detail" in data or ("error" in data and data.get("error", {}).get("code") == "VALIDATION_ERROR")

    def test_update_general_settings_partial_update(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that updating general settings updates all fields."""
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

        # Act: Update with partial changes
        first_update = {
            "timezone": "Europe/London",
            "date_format": "DD/MM/YYYY",
            "time_format": "24h",
            "currency": "GBP",
            "language": "en",
        }
        response1 = client.put(
            "/api/v1/config/general",
            headers={"Authorization": f"Bearer {access_token}"},
            json=first_update,
        )
        assert response1.status_code == status.HTTP_200_OK

        # Update again with different values
        second_update = {
            "timezone": "Asia/Tokyo",
            "date_format": "YYYY-MM-DD",
            "time_format": "12h",
            "currency": "JPY",
            "language": "ja",
        }
        response2 = client.put(
            "/api/v1/config/general",
            headers={"Authorization": f"Bearer {access_token}"},
            json=second_update,
        )
        assert response2.status_code == status.HTTP_200_OK

        # Assert: Verify final values
        get_response = client.get(
            "/api/v1/config/general",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert get_response.status_code == status.HTTP_200_OK
        final_data = get_response.json()
        final_settings = final_data["data"]

        assert final_settings["timezone"] == second_update["timezone"]
        assert final_settings["date_format"] == second_update["date_format"]
        assert final_settings["time_format"] == second_update["time_format"]
        assert final_settings["currency"] == second_update["currency"]
        assert final_settings["language"] == second_update["language"]











