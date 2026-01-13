"""Flow Run schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Flow Run schemas
class FlowRunBase(BaseModel):
    """Base schema for flow run."""

    flow_id: UUID | None = Field(None, description="Flow ID")
    entity_type: str = Field(..., description="Entity type", max_length=100)
    entity_id: UUID = Field(..., description="Entity ID")
    status: str = Field("pending", description="Flow run status", max_length=50)
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class FlowRunCreate(FlowRunBase):
    """Schema for creating a flow run."""

    pass


class FlowRunUpdate(BaseModel):
    """Schema for updating a flow run."""

    status: str | None = Field(None, description="Flow run status", max_length=50)
    error_message: str | None = Field(None, description="Error message if failed")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class FlowRunResponse(FlowRunBase):
    """Schema for flow run response."""

    id: UUID
    tenant_id: UUID
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FlowRunStatsResponse(BaseModel):
    """Schema for flow run statistics."""

    total: int = Field(..., description="Total flow runs")
    pending: int = Field(..., description="Pending flow runs")
    running: int = Field(..., description="Running flow runs")
    completed: int = Field(..., description="Completed flow runs")
    failed: int = Field(..., description="Failed flow runs")
