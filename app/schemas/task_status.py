"""Task Status schemas for API requests and responses."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TaskStatusBase(BaseModel):
    """Base schema for task status."""

    name: str = Field(..., description="Status name", max_length=50)
    type: str = Field(..., description="Status type: open, in_progress, closed")
    color: str = Field(..., description="Hex color code", max_length=7)
    order: int = Field(default=0, description="Display order")


class TaskStatusCreate(TaskStatusBase):
    """Schema for creating a task status."""

    pass


class TaskStatusUpdate(BaseModel):
    """Schema for updating a task status."""

    name: str | None = Field(None, description="Status name", max_length=50)
    type: str | None = Field(None, description="Status type")
    color: str | None = Field(None, description="Hex color code", max_length=7)
    order: int | None = Field(None, description="Display order")


class TaskStatusResponse(TaskStatusBase):
    """Schema for task status response."""

    id: UUID
    tenant_id: UUID
    is_system: bool

    model_config = ConfigDict(from_attributes=True)
