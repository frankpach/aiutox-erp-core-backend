"""Pydantic schemas for system configuration."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConfigCreate(BaseModel):
    """Schema for creating a configuration entry."""

    tenant_id: UUID = Field(..., description="Tenant ID for multi-tenancy isolation")
    module: str = Field(
        ..., min_length=1, max_length=100, description="Module name (e.g., 'products', 'inventory')"
    )
    key: str = Field(
        ..., min_length=1, max_length=255, description="Configuration key"
    )
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
    tenant_id: UUID = Field(
        ..., description="Tenant ID for multi-tenancy isolation"
    )
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
    model_count: int = Field(..., description="Number of SQLAlchemy models in the module")


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




