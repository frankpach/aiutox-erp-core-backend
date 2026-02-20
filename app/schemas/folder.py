"""Pydantic schemas for folder management."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FolderBase(BaseModel):
    """Base folder schema."""

    name: str = Field(..., min_length=1, max_length=255, description="Folder name")
    description: str | None = Field(None, description="Folder description")
    color: str | None = Field(
        None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Folder color (hex)"
    )
    icon: str | None = Field(None, max_length=50, description="Folder icon name")
    parent_id: UUID | None = Field(
        None, description="Parent folder ID (null for root folders)"
    )
    entity_type: str | None = Field(
        None, max_length=50, description="Entity type (e.g., 'product', 'order')"
    )
    entity_id: UUID | None = Field(None, description="Entity ID")
    metadata: dict | None = Field(None, description="Additional metadata")


class FolderCreate(FolderBase):
    """Schema for creating a folder."""

    pass


class FolderUpdate(BaseModel):
    """Schema for updating a folder."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str | None = Field(None, max_length=50)
    parent_id: UUID | None = None
    metadata: dict | None = None


class FolderResponse(FolderBase):
    """Schema for folder response."""

    id: UUID
    tenant_id: UUID
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    path: str | None = Field(None, description="Full path of the folder")
    depth: int = Field(0, description="Depth in hierarchy (0 for root)")

    model_config = ConfigDict(from_attributes=True)


class FolderTreeItem(FolderResponse):
    """Folder with children for tree structure."""

    children: list["FolderTreeItem"] = Field(default_factory=list)
    file_count: int = Field(0, description="Number of files in this folder")


class FolderContentResponse(BaseModel):
    """Response for folder content (files and subfolders)."""

    folder: FolderResponse
    folders: list[FolderResponse] = Field(default_factory=list)
    files: list = Field(default_factory=list)  # Will be FileResponse
    total_folders: int = 0
    total_files: int = 0


class MoveItemsRequest(BaseModel):
    """Request to move files/folders to a folder."""

    file_ids: list[UUID] = Field(default_factory=list, description="File IDs to move")
    folder_ids: list[UUID] = Field(
        default_factory=list, description="Folder IDs to move"
    )
    target_folder_id: UUID | None = Field(
        None, description="Target folder ID (null for root)"
    )


class FolderPermissionRequest(BaseModel):
    """Schema for folder permission request."""

    target_type: str = Field(
        ..., description="Target type: 'user', 'role', 'organization'"
    )
    target_id: UUID = Field(..., description="Target ID")
    can_view: bool = Field(default=True, description="Can view folder")
    can_create_files: bool = Field(
        default=False, description="Can create files in folder"
    )
    can_create_folders: bool = Field(default=False, description="Can create subfolders")
    can_edit: bool = Field(default=False, description="Can edit folder")
    can_delete: bool = Field(default=False, description="Can delete folder")


class FolderPermissionResponse(BaseModel):
    """Schema for folder permission response."""

    id: UUID
    folder_id: UUID
    target_type: str
    target_id: UUID
    can_view: bool
    can_create_files: bool
    can_create_folders: bool
    can_edit: bool
    can_delete: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
