"""Tag schemas for API requests and responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TagBase(BaseModel):
    """Base schema for tag."""

    name: str = Field(..., description="Tag name", min_length=1, max_length=100)
    color: str | None = Field(None, description="Hex color code (e.g., #FF5733)", max_length=7)
    description: str | None = Field(None, description="Tag description", max_length=500)
    category_id: UUID | None = Field(None, description="Category ID")


class TagCreate(TagBase):
    """Schema for creating a tag."""

    pass


class TagUpdate(BaseModel):
    """Schema for updating a tag."""

    name: str | None = Field(None, description="Tag name", min_length=1, max_length=100)
    color: str | None = Field(None, description="Hex color code", max_length=7)
    description: str | None = Field(None, description="Tag description", max_length=500)
    category_id: UUID | None = Field(None, description="Category ID")


class TagResponse(TagBase):
    """Schema for tag response."""

    id: UUID
    tenant_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagCategoryBase(BaseModel):
    """Base schema for tag category."""

    name: str = Field(..., description="Category name", min_length=1, max_length=100)
    color: str | None = Field(None, description="Hex color code", max_length=7)
    description: str | None = Field(None, description="Category description", max_length=500)
    parent_id: UUID | None = Field(None, description="Parent category ID")
    sort_order: int = Field(default=0, description="Sort order")


class TagCategoryCreate(TagCategoryBase):
    """Schema for creating a tag category."""

    pass


class TagCategoryResponse(TagCategoryBase):
    """Schema for tag category response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

