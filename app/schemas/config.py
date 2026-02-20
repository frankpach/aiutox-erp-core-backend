"""Pydantic schemas for system configuration."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModuleNavigationSettingRequirementSchema(BaseModel):
    """Requirement for showing a navigation item based on module settings."""

    model_config = ConfigDict(from_attributes=True)

    module: str = Field(..., description="Module ID that owns the setting")
    key: str = Field(..., description="Configuration key to evaluate")
    value: Any | None = Field(
        None,
        description="Optional value requirement; if provided, the setting must match this value",
    )


class ModuleNavigationItemSchema(BaseModel):
    """Navigation item published by a module."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique identifier for the navigation item")
    label: str = Field(..., description="Localized label for the item")
    path: str = Field(..., description="Absolute path that the item should open")
    permission: str | None = Field(
        None, description="Permission required to show the item (if any)"
    )
    icon: str | None = Field(None, description="Icon token understood by the frontend")
    category: str | None = Field(
        None, description="Optional category override (defaults to module grouping)"
    )
    order: int = Field(0, description="Display order within its category")
    badge: int | None = Field(None, description="Optional badge count for the item")
    requires_module_setting: ModuleNavigationSettingRequirementSchema | None = Field(
        None,
        description="Requirement definition to display the item",
    )


class ConfigCreate(BaseModel):
    """Schema for creating a configuration entry."""

    tenant_id: UUID = Field(..., description="Tenant ID for multi-tenancy isolation")
    module: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Module name (e.g., 'products', 'inventory')",
    )
    key: str = Field(..., min_length=1, max_length=255, description="Configuration key")
    value: dict[str, Any] | list | str | int | float | bool = Field(
        ..., description="Configuration value (JSON)"
    )


class ConfigUpdate(BaseModel):
    """Schema for updating a configuration entry."""

    value: dict[str, Any] | list | str | int | float | bool = Field(
        ..., description="Configuration value (JSON)"
    )


class ConfigResponse(BaseModel):
    """Response schema for system configuration."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Configuration ID")
    tenant_id: UUID = Field(..., description="Tenant ID for multi-tenancy isolation")
    module: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Module name (e.g., 'products', 'inventory')",
    )
    key: str = Field(..., min_length=1, max_length=255, description="Configuration key")
    value: dict[str, Any] | list | str | int | float | bool = Field(
        ..., description="Configuration value (JSON)"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class ModuleConfigResponse(BaseModel):
    """Response schema for module configuration (all keys)."""

    model_config = ConfigDict(from_attributes=True)

    module: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Module name (e.g., 'products', 'inventory')",
    )
    config: dict[str, Any] = Field(
        ..., description="Dictionary of all configuration keys and values"
    )


class ModuleInfoResponse(BaseModel):
    """Response schema for detailed module information."""

    id: str = Field(..., description="Module identifier (e.g., 'products', 'auth')")
    name: str = Field(..., description="Human-readable module name")
    type: str = Field(..., description="Module type: 'core' or 'business'")
    enabled: bool = Field(..., description="Whether the module is enabled")
    dependencies: list[str] = Field(
        default_factory=list, description="List of module IDs this module depends on"
    )
    description: str = Field(default="", description="Module description")
    has_router: bool = Field(..., description="Whether the module has API endpoints")
    model_count: int = Field(
        ..., description="Number of SQLAlchemy models in the module"
    )
    navigation_items: list[ModuleNavigationItemSchema] = Field(
        default_factory=list,
        description="Primary navigation entries exposed by the module",
    )
    settings_links: list[ModuleNavigationItemSchema] = Field(
        default_factory=list,
        description="Configuration entries that must show under Configuración",
    )


class ModuleListItem(BaseModel):
    """Schema for a single module in a list."""

    id: str = Field(..., description="Module identifier")
    name: str = Field(..., description="Human-readable module name")
    type: str = Field(..., description="Module type: 'core' or 'business'")
    enabled: bool = Field(..., description="Whether the module is enabled")
    dependencies: list[str] = Field(
        default_factory=list, description="List of module IDs this module depends on"
    )
    description: str = Field(default="", description="Module description")
    navigation_items: list[ModuleNavigationItemSchema] = Field(
        default_factory=list,
        description="Primary navigation entries exposed by the module",
    )
    settings_links: list[ModuleNavigationItemSchema] = Field(
        default_factory=list,
        description="Configuration entries that must show under Configuración",
    )


class GeneralSettingsRequest(BaseModel):
    """Schema for updating general system settings."""

    timezone: str = Field(
        default="America/Mexico_City",
        description="Timezone (e.g., 'America/Mexico_City', 'UTC')",
        max_length=100,
    )
    date_format: str = Field(
        default="DD/MM/YYYY",
        description="Date format (e.g., 'DD/MM/YYYY', 'MM/DD/YYYY', 'YYYY-MM-DD')",
        max_length=20,
    )
    time_format: str = Field(
        default="24h",
        description="Time format: '12h' or '24h'",
        pattern="^(12h|24h)$",
    )
    currency: str = Field(
        default="MXN",
        description="Currency code (ISO 4217, e.g., 'MXN', 'USD', 'EUR')",
        max_length=3,
        min_length=3,
    )
    language: str = Field(
        default="es",
        description="Language code (ISO 639-1, e.g., 'es', 'en', 'fr')",
        max_length=5,
        min_length=2,
    )


class ThemePresetCreate(BaseModel):
    """Schema for creating a theme preset."""

    name: str = Field(..., min_length=1, max_length=255, description="Preset name")
    description: str | None = Field(None, description="Optional description")
    config: dict[str, Any] = Field(..., description="Theme configuration dictionary")
    is_default: bool = Field(
        False, description="Whether this should be the default preset"
    )


class ThemePresetUpdate(BaseModel):
    """Schema for updating a theme preset."""

    name: str | None = Field(
        None, min_length=1, max_length=255, description="Preset name"
    )
    description: str | None = Field(None, description="Optional description")
    config: dict[str, Any] | None = Field(
        None, description="Theme configuration dictionary"
    )
    is_default: bool | None = Field(
        None, description="Whether this should be the default preset"
    )


class ThemePresetResponse(BaseModel):
    """Response schema for theme preset."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Preset ID")
    tenant_id: UUID = Field(..., description="Tenant ID")
    name: str = Field(..., description="Preset name")
    description: str | None = Field(None, description="Optional description")
    config: dict[str, Any] = Field(..., description="Theme configuration dictionary")
    is_default: bool = Field(..., description="Whether this is the default preset")
    is_system: bool = Field(..., description="Whether this is a system preset")
    created_by: UUID | None = Field(None, description="User who created this preset")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class GeneralSettingsResponse(BaseModel):
    """Schema for general system settings response."""

    timezone: str = Field(..., description="Timezone")
    date_format: str = Field(..., description="Date format")
    time_format: str = Field(..., description="Time format")
    currency: str = Field(..., description="Currency code")
    language: str = Field(..., description="Language code")
