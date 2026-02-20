"""File schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.tag import TagResponse


class FileBase(BaseModel):
    """Base schema for file."""

    name: str = Field(..., description="File name", max_length=255)
    description: str | None = Field(None, description="File description")
    entity_type: str | None = Field(
        None, description="Entity type (e.g., 'product', 'order')"
    )
    entity_id: UUID | None = Field(None, description="Entity ID")


class FileCreate(FileBase):
    """Schema for creating a file (upload)."""

    permissions: list["FilePermissionRequest"] | None = Field(
        None, description="Initial permissions to assign to the file"
    )


class FileUpdate(BaseModel):
    """Schema for updating a file."""

    name: str | None = Field(None, description="File name", max_length=255)
    description: str | None = Field(None, description="File description")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class FileResponse(FileBase):
    """Schema for file response."""

    id: UUID
    tenant_id: UUID
    original_name: str
    mime_type: str
    size: int
    extension: str | None
    storage_backend: str
    storage_path: str
    storage_url: str | None
    version_number: int
    is_current: bool
    deleted_at: datetime | None = Field(
        None, description="Timestamp when file was deleted (soft delete)"
    )
    folder_id: UUID | None = Field(None, description="Folder ID (null for root)")
    uploaded_by: UUID | None
    uploaded_by_user: dict[str, Any] | None = Field(
        None,
        description="User information (name, email) who uploaded the file",
    )
    tags: list[TagResponse] | None = Field(
        None,
        description="Tags associated with the file",
    )
    metadata: dict[str, Any] | None = Field(
        None, alias="file_metadata", description="Additional metadata"
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class FileVersionResponse(BaseModel):
    """Schema for file version response."""

    id: UUID
    file_id: UUID
    version_number: int
    storage_path: str
    storage_backend: str
    size: int
    mime_type: str
    change_description: str | None
    created_by: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FilePermissionRequest(BaseModel):
    """Schema for file permission request."""

    target_type: str = Field(
        ..., description="Target type: 'user', 'role', 'organization'"
    )
    target_id: UUID = Field(..., description="Target ID")
    can_view: bool = Field(default=True, description="Can view file")
    can_download: bool = Field(default=True, description="Can download file")
    can_edit: bool = Field(default=False, description="Can edit file")
    can_delete: bool = Field(default=False, description="Can delete file")


class FilePermissionResponse(BaseModel):
    """Schema for file permission response."""

    id: UUID
    file_id: UUID
    target_type: str
    target_id: UUID
    can_view: bool
    can_download: bool
    can_edit: bool
    can_delete: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FileVersionCreate(BaseModel):
    """Schema for creating a file version."""

    change_description: str | None = Field(None, description="Description of changes")
