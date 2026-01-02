"""Theme preset service for managing theme presets."""

from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.config.service import ConfigService
from app.core.exceptions import APIException, raise_bad_request, raise_not_found
from app.models.theme_preset import ThemePreset


class ThemePresetService:
    """Service for managing theme presets."""

    def __init__(self, db: Session):
        """Initialize service with database session.

        Args:
            db: Database session
        """
        self.db = db
        self.config_service = ConfigService(db, use_cache=False, use_versioning=False)

    def list_presets(self, tenant_id: UUID) -> list[ThemePreset]:
        """List all presets for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            List of theme presets
        """
        return (
            self.db.query(ThemePreset)
            .filter(ThemePreset.tenant_id == tenant_id)
            .order_by(ThemePreset.is_system.desc(), ThemePreset.is_default.desc(), ThemePreset.name)
            .all()
        )

    def get_preset(self, preset_id: UUID, tenant_id: UUID) -> ThemePreset:
        """Get a preset by ID.

        Args:
            preset_id: Preset ID
            tenant_id: Tenant ID (for security)

        Returns:
            Theme preset

        Raises:
            APIException: If preset not found
        """
        preset = (
            self.db.query(ThemePreset)
            .filter(
                ThemePreset.id == preset_id,
                ThemePreset.tenant_id == tenant_id,
            )
            .first()
        )

        if not preset:
            raise_not_found("Theme preset", str(preset_id))

        return preset

    def create_preset(
        self,
        tenant_id: UUID,
        name: str,
        config: dict[str, Any],
        description: str | None = None,
        is_default: bool = False,
        created_by: UUID | None = None,
    ) -> ThemePreset:
        """Create a new theme preset.

        Args:
            tenant_id: Tenant ID
            name: Preset name
            config: Theme configuration dictionary
            description: Optional description
            is_default: Whether this should be the default preset
            created_by: User ID who created this preset

        Returns:
            Created theme preset

        Raises:
            APIException: If validation fails or preset with same name exists
        """
        # Validate name is not empty
        if not name or not name.strip():
            raise_bad_request("INVALID_PRESET_NAME", "Preset name cannot be empty")

        # Check if preset with same name already exists for this tenant
        existing = (
            self.db.query(ThemePreset)
            .filter(
                ThemePreset.tenant_id == tenant_id,
                ThemePreset.name == name.strip(),
            )
            .first()
        )

        if existing:
            raise_bad_request(
                "PRESET_NAME_EXISTS",
                f"Preset with name '{name}' already exists",
                details={"name": name},
            )

        # If setting as default, unset other defaults
        if is_default:
            self._unset_default(tenant_id)

        # Create preset
        preset = ThemePreset(
            tenant_id=tenant_id,
            name=name.strip(),
            description=description,
            config=config,
            is_default=is_default,
            is_system=False,  # User-created presets are never system presets
            created_by=created_by,
        )

        self.db.add(preset)
        self.db.commit()
        self.db.refresh(preset)

        return preset

    def update_preset(
        self,
        preset_id: UUID,
        tenant_id: UUID,
        name: str | None = None,
        description: str | None = None,
        config: dict[str, Any] | None = None,
        is_default: bool | None = None,
    ) -> ThemePreset:
        """Update a theme preset.

        Args:
            preset_id: Preset ID
            tenant_id: Tenant ID (for security)
            name: New name (optional)
            description: New description (optional)
            config: New config (optional)
            is_default: Whether to set as default (optional)

        Returns:
            Updated theme preset

        Raises:
            APIException: If preset not found, is system preset, or validation fails
        """
        preset = self.get_preset(preset_id, tenant_id)

        # System presets cannot be edited
        if preset.is_system:
            raise_bad_request(
                "CANNOT_EDIT_SYSTEM_PRESET",
                "System presets cannot be edited",
                details={"preset_id": str(preset_id), "preset_name": preset.name},
            )

        # Update fields
        if name is not None:
            if not name.strip():
                raise_bad_request("INVALID_PRESET_NAME", "Preset name cannot be empty")

            # Check if another preset with same name exists
            existing = (
                self.db.query(ThemePreset)
                .filter(
                    ThemePreset.tenant_id == tenant_id,
                    ThemePreset.name == name.strip(),
                    ThemePreset.id != preset_id,
                )
                .first()
            )

            if existing:
                raise_bad_request(
                    "PRESET_NAME_EXISTS",
                    f"Preset with name '{name}' already exists",
                    details={"name": name},
                )

            preset.name = name.strip()

        if description is not None:
            preset.description = description

        if config is not None:
            preset.config = config

        if is_default is not None:
            if is_default:
                self._unset_default(tenant_id)
            preset.is_default = is_default

        self.db.commit()
        self.db.refresh(preset)

        return preset

    def delete_preset(self, preset_id: UUID, tenant_id: UUID) -> None:
        """Delete a theme preset.

        Args:
            preset_id: Preset ID
            tenant_id: Tenant ID (for security)

        Raises:
            APIException: If preset not found or is system preset
        """
        preset = self.get_preset(preset_id, tenant_id)

        # System presets cannot be deleted
        if preset.is_system:
            raise_bad_request(
                "CANNOT_DELETE_SYSTEM_PRESET",
                "System presets cannot be deleted",
                details={"preset_id": str(preset_id), "preset_name": preset.name},
            )

        self.db.delete(preset)
        self.db.commit()

    def apply_preset(self, preset_id: UUID, tenant_id: UUID) -> dict[str, Any]:
        """Apply a preset as the active theme.

        Args:
            preset_id: Preset ID
            tenant_id: Tenant ID (for security)

        Returns:
            Applied theme configuration

        Raises:
            APIException: If preset not found
        """
        preset = self.get_preset(preset_id, tenant_id)

        # Apply preset config as active theme
        self.config_service.set_module_config(
            tenant_id=tenant_id,
            module="app_theme",
            config_dict=preset.config,
            user_id=None,  # System operation
            ip_address=None,
            user_agent=None,
        )

        return preset.config

    def set_default_preset(self, preset_id: UUID, tenant_id: UUID) -> ThemePreset:
        """Set a preset as the default for the tenant.

        Args:
            preset_id: Preset ID
            tenant_id: Tenant ID (for security)

        Returns:
            Updated preset

        Raises:
            APIException: If preset not found
        """
        preset = self.get_preset(preset_id, tenant_id)

        # Unset other defaults
        self._unset_default(tenant_id)

        # Set this as default
        preset.is_default = True
        self.db.commit()
        self.db.refresh(preset)

        return preset

    def _unset_default(self, tenant_id: UUID) -> None:
        """Unset default flag from all presets for a tenant.

        Args:
            tenant_id: Tenant ID
        """
        self.db.query(ThemePreset).filter(
            ThemePreset.tenant_id == tenant_id,
            ThemePreset.is_default == True,
        ).update({"is_default": False})
        self.db.commit()






