"""View schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Saved Filter schemas
class SavedFilterBase(BaseModel):
    """Base schema for saved filter."""

    name: str = Field(..., description="Filter name", max_length=255)
    description: str | None = Field(None, description="Filter description")
    module: str = Field(..., description="Module name (e.g., 'products', 'inventory')", max_length=50)
    filters: dict[str, Any] = Field(..., description="Filter conditions as JSON")
    is_default: bool = Field(False, description="Whether this is the default filter")
    is_shared: bool = Field(False, description="Whether filter is shared")


class SavedFilterCreate(SavedFilterBase):
    """Schema for creating a saved filter."""

    pass


class SavedFilterUpdate(BaseModel):
    """Schema for updating a saved filter."""

    name: str | None = Field(None, description="Filter name", max_length=255)
    description: str | None = Field(None, description="Filter description")
    filters: dict[str, Any] | None = Field(None, description="Filter conditions as JSON")
    is_default: bool | None = Field(None, description="Whether this is the default filter")
    is_shared: bool | None = Field(None, description="Whether filter is shared")


class SavedFilterResponse(SavedFilterBase):
    """Schema for saved filter response."""

    id: UUID
    tenant_id: UUID
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Custom View schemas
class CustomViewBase(BaseModel):
    """Base schema for custom view."""

    name: str = Field(..., description="View name", max_length=255)
    description: str | None = Field(None, description="View description")
    module: str = Field(..., description="Module name (e.g., 'products', 'inventory')", max_length=50)
    columns: dict[str, Any] = Field(..., description="Column configuration")
    sorting: dict[str, Any] | None = Field(None, description="Sorting configuration")
    grouping: dict[str, Any] | None = Field(None, description="Grouping configuration")
    filters: dict[str, Any] | None = Field(None, description="Associated filters")
    is_default: bool = Field(False, description="Whether this is the default view")
    is_shared: bool = Field(False, description="Whether view is shared")


class CustomViewCreate(CustomViewBase):
    """Schema for creating a custom view."""

    pass


class CustomViewUpdate(BaseModel):
    """Schema for updating a custom view."""

    name: str | None = Field(None, description="View name", max_length=255)
    description: str | None = Field(None, description="View description")
    columns: dict[str, Any] | None = Field(None, description="Column configuration")
    sorting: dict[str, Any] | None = Field(None, description="Sorting configuration")
    grouping: dict[str, Any] | None = Field(None, description="Grouping configuration")
    filters: dict[str, Any] | None = Field(None, description="Associated filters")
    is_default: bool | None = Field(None, description="Whether this is the default view")
    is_shared: bool | None = Field(None, description="Whether view is shared")


class CustomViewResponse(CustomViewBase):
    """Schema for custom view response."""

    id: UUID
    tenant_id: UUID
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# View Share schemas
class ViewShareBase(BaseModel):
    """Base schema for view share."""

    filter_id: UUID | None = Field(None, description="Shared filter ID")
    view_id: UUID | None = Field(None, description="Shared view ID")
    shared_with_user_id: UUID | None = Field(None, description="User ID to share with")
    shared_with_role: str | None = Field(None, description="Role to share with", max_length=50)


class ViewShareCreate(ViewShareBase):
    """Schema for creating a view share."""

    pass


class ViewShareResponse(ViewShareBase):
    """Schema for view share response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)








