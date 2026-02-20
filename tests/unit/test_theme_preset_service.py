"""Unit tests for ThemePresetService."""

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.config.theme_preset_service import ThemePresetService
from app.core.exceptions import APIException
from app.models.theme_preset import ThemePreset


class TestThemePresetService:
    """Test suite for ThemePresetService."""

    def test_list_presets_empty(self, db_session: Session, test_tenant):
        """Test listing presets when none exist."""
        service = ThemePresetService(db_session)
        tenant_id = test_tenant.id

        presets = service.list_presets(tenant_id)

        assert presets == []

    def test_list_presets_with_data(self, db_session: Session, test_tenant):
        """Test listing presets with existing data."""
        service = ThemePresetService(db_session)
        tenant_id = test_tenant.id

        # Create test presets
        preset1 = ThemePreset(
            tenant_id=tenant_id,
            name="Preset 1",
            config={"primary_color": "#000000"},
            is_default=True,
        )
        preset2 = ThemePreset(
            tenant_id=tenant_id,
            name="Preset 2",
            config={"primary_color": "#FFFFFF"},
            is_system=True,
        )
        db_session.add(preset1)
        db_session.add(preset2)
        db_session.commit()

        presets = service.list_presets(tenant_id)

        assert len(presets) == 2
        # System presets should come first, then defaults
        assert presets[0].is_system is True
        assert presets[1].is_default is True

    def test_get_preset_success(self, db_session: Session, test_tenant):
        """Test getting a preset by ID."""
        service = ThemePresetService(db_session)
        tenant_id = test_tenant.id

        # Create a preset
        preset = ThemePreset(
            tenant_id=tenant_id,
            name="Test Preset",
            config={"primary_color": "#000000"},
        )
        db_session.add(preset)
        db_session.commit()

        result = service.get_preset(preset.id, tenant_id)

        assert result.id == preset.id
        assert result.name == "Test Preset"

    def test_get_preset_not_found(self, db_session: Session, test_tenant):
        """Test getting a non-existent preset raises error."""
        service = ThemePresetService(db_session)
        tenant_id = test_tenant.id
        fake_id = uuid4()

        with pytest.raises(APIException) as exc_info:
            service.get_preset(fake_id, tenant_id)

        assert exc_info.value.code == "THEME_PRESET_NOT_FOUND"

    def test_get_preset_wrong_tenant(self, db_session: Session, test_tenant):
        """Test getting a preset from different tenant raises error."""
        service = ThemePresetService(db_session)
        tenant_id = test_tenant.id
        other_tenant_id = uuid4()

        # Create preset for test_tenant
        preset = ThemePreset(
            tenant_id=tenant_id,
            name="Test Preset",
            config={"primary_color": "#000000"},
        )
        db_session.add(preset)
        db_session.commit()

        # Try to get it with different tenant_id
        with pytest.raises(APIException) as exc_info:
            service.get_preset(preset.id, other_tenant_id)

        assert exc_info.value.code == "THEME_PRESET_NOT_FOUND"

    def test_create_preset_success(self, db_session: Session, test_tenant, test_user):
        """Test creating a preset successfully."""
        service = ThemePresetService(db_session)
        tenant_id = test_tenant.id

        config = {
            "primary_color": "#1976D2",
            "secondary_color": "#DC004E",
        }

        preset = service.create_preset(
            tenant_id=tenant_id,
            name="My Preset",
            config=config,
            description="Test description",
            created_by=test_user.id,
        )

        assert preset.name == "My Preset"
        assert preset.description == "Test description"
        assert preset.config == config
        assert preset.tenant_id == tenant_id
        assert preset.is_system is False
        assert preset.is_default is False
        assert preset.created_by == test_user.id

    def test_create_preset_empty_name(self, db_session: Session, test_tenant):
        """Test creating a preset with empty name raises error."""
        service = ThemePresetService(db_session)
        tenant_id = test_tenant.id

        with pytest.raises(APIException) as exc_info:
            service.create_preset(
                tenant_id=tenant_id,
                name="",
                config={"primary_color": "#000000"},
            )

        assert exc_info.value.code == "INVALID_PRESET_NAME"

    def test_create_preset_duplicate_name(self, db_session: Session, test_tenant):
        """Test creating a preset with duplicate name raises error."""
        service = ThemePresetService(db_session)
        tenant_id = test_tenant.id

        # Create first preset
        service.create_preset(
            tenant_id=tenant_id,
            name="Existing Preset",
            config={"primary_color": "#000000"},
        )

        # Try to create another with same name
        with pytest.raises(APIException) as exc_info:
            service.create_preset(
                tenant_id=tenant_id,
                name="Existing Preset",
                config={"primary_color": "#FFFFFF"},
            )

        assert exc_info.value.code == "PRESET_NAME_EXISTS"

    def test_create_preset_as_default(self, db_session: Session, test_tenant):
        """Test creating a preset as default unsets other defaults."""
        service = ThemePresetService(db_session)
        tenant_id = test_tenant.id

        # Create first default preset
        preset1 = service.create_preset(
            tenant_id=tenant_id,
            name="Default 1",
            config={"primary_color": "#000000"},
            is_default=True,
        )

        assert preset1.is_default is True

        # Create second default preset
        preset2 = service.create_preset(
            tenant_id=tenant_id,
            name="Default 2",
            config={"primary_color": "#FFFFFF"},
            is_default=True,
        )

        assert preset2.is_default is True

        # First preset should no longer be default
        db_session.refresh(preset1)
        assert preset1.is_default is False

    def test_update_preset_success(self, db_session: Session, test_tenant):
        """Test updating a preset successfully."""
        service = ThemePresetService(db_session)
        tenant_id = test_tenant.id

        # Create preset
        preset = service.create_preset(
            tenant_id=tenant_id,
            name="Original Name",
            config={"primary_color": "#000000"},
            description="Original description",
        )

        # Update preset
        updated = service.update_preset(
            preset_id=preset.id,
            tenant_id=tenant_id,
            name="Updated Name",
            description="Updated description",
            config={"primary_color": "#FFFFFF"},
        )

        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"
        assert updated.config == {"primary_color": "#FFFFFF"}

    def test_update_preset_system_preset(self, db_session: Session, test_tenant):
        """Test updating a system preset raises error."""
        service = ThemePresetService(db_session)
        tenant_id = test_tenant.id

        # Create system preset
        preset = ThemePreset(
            tenant_id=tenant_id,
            name="System Preset",
            config={"primary_color": "#000000"},
            is_system=True,
        )
        db_session.add(preset)
        db_session.commit()

        # Try to update
        with pytest.raises(APIException) as exc_info:
            service.update_preset(
                preset_id=preset.id,
                tenant_id=tenant_id,
                name="Updated Name",
            )

        assert exc_info.value.code == "CANNOT_EDIT_SYSTEM_PRESET"

    def test_update_preset_duplicate_name(self, db_session: Session, test_tenant):
        """Test updating preset with duplicate name raises error."""
        service = ThemePresetService(db_session)
        tenant_id = test_tenant.id

        # Create two presets
        preset1 = service.create_preset(
            tenant_id=tenant_id,
            name="Preset 1",
            config={"primary_color": "#000000"},
        )
        assert preset1.name == "Preset 1"
        preset2 = service.create_preset(
            tenant_id=tenant_id,
            name="Preset 2",
            config={"primary_color": "#FFFFFF"},
        )

        # Try to rename preset2 to preset1's name
        with pytest.raises(APIException) as exc_info:
            service.update_preset(
                preset_id=preset2.id,
                tenant_id=tenant_id,
                name="Preset 1",
            )

        assert exc_info.value.code == "PRESET_NAME_EXISTS"

    def test_update_preset_set_as_default(self, db_session: Session, test_tenant):
        """Test updating preset to be default unsets other defaults."""
        service = ThemePresetService(db_session)
        tenant_id = test_tenant.id

        # Create two presets, first one is default
        preset1 = service.create_preset(
            tenant_id=tenant_id,
            name="Preset 1",
            config={"primary_color": "#000000"},
            is_default=True,
        )
        preset2 = service.create_preset(
            tenant_id=tenant_id,
            name="Preset 2",
            config={"primary_color": "#FFFFFF"},
            is_default=False,
        )

        # Set preset2 as default
        service.update_preset(
            preset_id=preset2.id,
            tenant_id=tenant_id,
            is_default=True,
        )

        # Preset1 should no longer be default
        db_session.refresh(preset1)
        assert preset1.is_default is False

        # Preset2 should be default
        db_session.refresh(preset2)
        assert preset2.is_default is True

    def test_delete_preset_success(self, db_session: Session, test_tenant):
        """Test deleting a preset successfully."""
        service = ThemePresetService(db_session)
        tenant_id = test_tenant.id

        # Create preset
        preset = service.create_preset(
            tenant_id=tenant_id,
            name="To Delete",
            config={"primary_color": "#000000"},
        )

        preset_id = preset.id

        # Delete preset
        service.delete_preset(preset_id, tenant_id)

        # Verify it's gone
        with pytest.raises(APIException):
            service.get_preset(preset_id, tenant_id)

    def test_delete_preset_system_preset(self, db_session: Session, test_tenant):
        """Test deleting a system preset raises error."""
        service = ThemePresetService(db_session)
        tenant_id = test_tenant.id

        # Create system preset
        preset = ThemePreset(
            tenant_id=tenant_id,
            name="System Preset",
            config={"primary_color": "#000000"},
            is_system=True,
        )
        db_session.add(preset)
        db_session.commit()

        # Try to delete
        with pytest.raises(APIException) as exc_info:
            service.delete_preset(preset.id, tenant_id)

        assert exc_info.value.code == "CANNOT_DELETE_SYSTEM_PRESET"

    def test_apply_preset_success(self, db_session: Session, test_tenant):
        """Test applying a preset successfully."""
        service = ThemePresetService(db_session)
        tenant_id = test_tenant.id

        config = {
            "primary_color": "#1976D2",
            "secondary_color": "#DC004E",
        }

        # Create preset
        preset = service.create_preset(
            tenant_id=tenant_id,
            name="To Apply",
            config=config,
        )

        # Apply preset
        applied_config = service.apply_preset(preset.id, tenant_id)

        assert applied_config == config

        # Verify config was applied via ConfigService
        applied_primary = service.config_service.get(tenant_id, "app_theme", "primary_color")
        assert applied_primary == "#1976D2"

    def test_set_default_preset_success(self, db_session: Session, test_tenant):
        """Test setting a preset as default successfully."""
        service = ThemePresetService(db_session)
        tenant_id = test_tenant.id

        # Create preset
        preset = service.create_preset(
            tenant_id=tenant_id,
            name="To Set Default",
            config={"primary_color": "#000000"},
            is_default=False,
        )

        # Set as default
        updated = service.set_default_preset(preset.id, tenant_id)

        assert updated.is_default is True

    def test_set_default_preset_unsets_others(self, db_session: Session, test_tenant):
        """Test setting a preset as default unsets other defaults."""
        service = ThemePresetService(db_session)
        tenant_id = test_tenant.id

        # Create two presets, first one is default
        preset1 = service.create_preset(
            tenant_id=tenant_id,
            name="Preset 1",
            config={"primary_color": "#000000"},
            is_default=True,
        )
        preset2 = service.create_preset(
            tenant_id=tenant_id,
            name="Preset 2",
            config={"primary_color": "#FFFFFF"},
            is_default=False,
        )

        # Set preset2 as default
        service.set_default_preset(preset2.id, tenant_id)

        # Preset1 should no longer be default
        db_session.refresh(preset1)
        assert preset1.is_default is False

        # Preset2 should be default
        db_session.refresh(preset2)
        assert preset2.is_default is True

    def test_multi_tenant_isolation(self, db_session: Session, test_tenant):
        """Test that presets are isolated by tenant."""
        service = ThemePresetService(db_session)
        tenant_id_1 = test_tenant.id
        tenant_id_2 = uuid4()

        # Create preset for tenant 1
        preset1 = service.create_preset(
            tenant_id=tenant_id_1,
            name="Tenant 1 Preset",
            config={"primary_color": "#000000"},
        )

        # List presets for tenant 2 (should be empty)
        presets_tenant2 = service.list_presets(tenant_id_2)
        assert len(presets_tenant2) == 0

        # List presets for tenant 1 (should have the preset)
        presets_tenant1 = service.list_presets(tenant_id_1)
        assert len(presets_tenant1) == 1
        assert presets_tenant1[0].id == preset1.id

        # Try to get preset1 with tenant_id_2 (should fail)
        with pytest.raises(APIException):
            service.get_preset(preset1.id, tenant_id_2)

