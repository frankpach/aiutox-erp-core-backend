"""Activity schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ActivityBase(BaseModel):
    """Base schema for activity."""

    entity_type: str = Field(..., description="Entity type (e.g., 'product', 'order')", max_length=50)
    entity_id: UUID = Field(..., description="Entity ID")
    activity_type: str = Field(..., description="Activity type (e.g., 'comment', 'call')", max_length=50)
    title: str = Field(..., description="Activity title", max_length=255)
    description: str | None = Field(None, description="Activity description")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class ActivityCreate(ActivityBase):
    """Schema for creating an activity."""

    pass


class ActivityUpdate(BaseModel):
    """Schema for updating an activity."""

    title: str | None = Field(None, description="Activity title", max_length=255)
    description: str | None = Field(None, description="Activity description")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class ActivityResponse(ActivityBase):
    """Schema for activity response."""

    id: UUID
    tenant_id: UUID
    user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] | None = Field(None, alias="activity_metadata", description="Additional metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

