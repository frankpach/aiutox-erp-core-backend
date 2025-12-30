"""Integration tests for theme configuration endpoints."""

from fastapi import status

from app.models.module_role import ModuleRole
from app.services.auth_service import AuthService


class TestThemeConfig:
    """Test suite for theme configuration endpoints."""

    def test_get_theme_config_requires_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that getting theme config requires config.view permission."""
        # Arrange: User without config permission
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to get theme config
        response = client.get(
            "/api/v1/config/app_theme",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"

    def test_get_theme_config_with_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that user with config.view can get theme config."""
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

        # Act: Get theme config
        response = client.get(
            "/api/v1/config/app_theme",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["module"] == "app_theme"
        assert isinstance(data["data"]["config"], dict)

    def test_get_theme_config_returns_defaults_when_empty(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that GET /api/v1/config/app_theme returns defaults when no theme is set."""
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

        # Act: Get theme config
        response = client.get(
            "/api/v1/config/app_theme",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return default values
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        config = data["data"]["config"]

        # Verify default colors exist
        assert "primary_color" in config
        assert "secondary_color" in config
        assert "background_color" in config

    def test_set_theme_config_requires_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that setting theme config requires config.edit permission."""
        # Arrange: User without config.edit permission
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to set theme config
        theme_data = {
            "primary_color": "#1976D2",
            "secondary_color": "#DC004E",
        }
        response = client.post(
            "/api/v1/config/app_theme",
            headers={"Authorization": f"Bearer {access_token}"},
            json=theme_data,
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"

    def test_set_theme_config_with_valid_colors(
        self, client, db_session, test_user, test_tenant
    ):
        """Test setting theme config with valid hex colors."""
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

        # Act: Set theme config with valid colors
        theme_data = {
            "primary_color": "#1976D2",
            "secondary_color": "#DC004E",
            "accent_color": "#FFC107",
            "background_color": "#FFFFFF",
        }
        response = client.post(
            "/api/v1/config/app_theme",
            headers={"Authorization": f"Bearer {access_token}"},
            json=theme_data,
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "data" in data
        assert data["data"]["module"] == "app_theme"
        assert data["data"]["config"]["primary_color"] == "#1976D2"
        assert data["data"]["config"]["secondary_color"] == "#DC004E"

    def test_set_theme_config_rejects_invalid_color_format(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that theme config rejects invalid color formats."""
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

        # Act: Try to set theme with invalid color (not hex format)
        theme_data = {
            "primary_color": "blue",  # Invalid - not hex format
        }
        response = client.post(
            "/api/v1/config/app_theme",
            headers={"Authorization": f"Bearer {access_token}"},
            json=theme_data,
        )

        # Assert: Should fail with validation error
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "INVALID_COLOR_FORMAT"
        assert "primary_color" in data["error"]["message"]
        assert "#RRGGBB" in data["error"]["message"]

    def test_set_theme_config_rejects_invalid_hex_length(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that theme config rejects colors with wrong hex length."""
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

        # Act: Try to set theme with invalid hex length
        theme_data = {
            "primary_color": "#1976D",  # Invalid - only 5 hex digits
        }
        response = client.post(
            "/api/v1/config/app_theme",
            headers={"Authorization": f"Bearer {access_token}"},
            json=theme_data,
        )

        # Assert: Should fail with validation error
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "INVALID_COLOR_FORMAT"

    def test_set_theme_config_rejects_invalid_hex_characters(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that theme config rejects colors with invalid hex characters."""
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

        # Act: Try to set theme with invalid hex characters
        theme_data = {
            "primary_color": "#GGGGGG",  # Invalid - G is not hex
        }
        response = client.post(
            "/api/v1/config/app_theme",
            headers={"Authorization": f"Bearer {access_token}"},
            json=theme_data,
        )

        # Assert: Should fail with validation error
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "INVALID_COLOR_FORMAT"

    def test_update_theme_property_with_valid_color(
        self, client, db_session, test_user, test_tenant
    ):
        """Test updating a single theme property with valid color."""
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

        # Act: Update primary_color
        response = client.put(
            "/api/v1/config/app_theme/primary_color",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"value": "#FF5722"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["value"] == "#FF5722"

    def test_update_theme_property_rejects_invalid_color(
        self, client, db_session, test_user, test_tenant
    ):
        """Test updating theme property rejects invalid color."""
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

        # Act: Try to update with invalid color
        response = client.put(
            "/api/v1/config/app_theme/primary_color",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"value": "red"},
        )

        # Assert: Should fail
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "INVALID_COLOR_FORMAT"

    def test_update_theme_property_non_color_field(
        self, client, db_session, test_user, test_tenant
    ):
        """Test updating non-color theme properties (like logos)."""
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

        # Act: Update logo_primary (not a color field, no validation)
        response = client.put(
            "/api/v1/config/app_theme/logo_primary",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"value": "/assets/logos/custom-logo.png"},
        )

        # Assert: Should succeed without color validation
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["value"] == "/assets/logos/custom-logo.png"

    def test_theme_config_persists_across_requests(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that theme configuration persists across requests."""
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

        # Set theme
        theme_data = {
            "primary_color": "#E91E63",
            "secondary_color": "#9C27B0",
        }
        set_response = client.post(
            "/api/v1/config/app_theme",
            headers={"Authorization": f"Bearer {access_token}"},
            json=theme_data,
        )
        assert set_response.status_code == status.HTTP_201_CREATED

        # Act: Get theme in a new request
        get_response = client.get(
            "/api/v1/config/app_theme",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return saved theme
        assert get_response.status_code == status.HTTP_200_OK
        data = get_response.json()
        config = data["data"]["config"]
        assert config["primary_color"] == "#E91E63"
        assert config["secondary_color"] == "#9C27B0"










