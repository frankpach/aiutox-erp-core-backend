"""Schemas para versionado de configuraciones."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConfigVersionResponse(BaseModel):
    """Response schema for a configuration version."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Version ID")
    version_number: int = Field(..., description="Sequential version number")
    value: Any = Field(..., description="Configuration value at this version")
    change_type: str = Field(..., description="Type of change: create, update, delete")
    changed_by: UUID | None = Field(None, description="User who made the change")
    change_reason: str | None = Field(None, description="Reason for the change")
    created_at: datetime = Field(..., description="Timestamp of this version")
    change_metadata: dict[str, Any] | None = Field(
        None, description="Additional metadata"
    )


class ConfigVersionListResponse(BaseModel):
    """Response schema for list of configuration versions."""

    versions: list[ConfigVersionResponse] = Field(..., description="List of versions")
    total: int = Field(..., description="Total number of versions")
    module: str = Field(..., description="Module name")
    key: str = Field(..., description="Configuration key")


class ConfigRollbackRequest(BaseModel):
    """Request schema for rolling back to a version."""

    version_number: int = Field(..., description="Version number to rollback to", ge=1)
    reason: str | None = Field(None, description="Reason for rollback", max_length=500)


class CacheStatsResponse(BaseModel):
    """Response schema for cache statistics."""

    enabled: bool = Field(..., description="Whether cache is enabled")
    status: str = Field(..., description="Cache status: connected, disabled, error")
    total_keys: int | None = Field(None, description="Total number of cached keys")
    ttl: int | None = Field(None, description="TTL in seconds")
    memory_used: str | None = Field(None, description="Memory used by cache")
    error: str | None = Field(None, description="Error message if status is error")
