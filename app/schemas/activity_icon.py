"""
Activity Icon Configuration Schemas
Pydantic schemas for activity icon configuration API
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ActivityIconConfigBase(BaseModel):
    """Base schema for activity icon configuration"""

    activity_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Type of activity (task, meeting, event, etc.)",
    )
    status: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Status of the activity (todo, in_progress, done, etc.)",
    )
    icon: str = Field(
        ..., min_length=1, max_length=10, description="Icon character or emoji"
    )
    class_name: str | None = Field(
        None, max_length=100, description="CSS classes for styling"
    )


class ActivityIconConfigCreate(ActivityIconConfigBase):
    """Schema for creating a new activity icon configuration"""

    pass


class ActivityIconConfigUpdate(BaseModel):
    """Schema for updating an existing activity icon configuration"""

    activity_type: str | None = Field(None, min_length=1, max_length=50)
    status: str | None = Field(None, min_length=1, max_length=50)
    icon: str | None = Field(None, min_length=1, max_length=10)
    class_name: str | None = Field(None, max_length=100)
    is_active: bool | None = None


class ActivityIconConfigResponse(ActivityIconConfigBase):
    """Schema for activity icon configuration response"""

    id: UUID
    tenant_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityIconConfigBulkUpdate(BaseModel):
    """Schema for bulk updating activity icon configurations"""

    configs: dict[str, dict[str, str]] = Field(
        ..., description="Nested dictionary: {activity_type: {status: icon}}"
    )
