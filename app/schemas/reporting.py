"""Reporting schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReportDefinitionCreate(BaseModel):
    """Schema for creating a report definition."""

    name: str = Field(..., description="Report name", min_length=1, max_length=255)
    description: str | None = Field(None, description="Report description")
    data_source_type: str = Field(..., description="Data source type (e.g., 'products')")
    visualization_type: str = Field(
        ..., description="Visualization type: 'table', 'chart', 'kpi'"
    )
    filters: dict[str, Any] | None = Field(None, description="Filter configuration")
    config: dict[str, Any] | None = Field(
        None, description="Visualization-specific configuration"
    )


class ReportDefinitionUpdate(BaseModel):
    """Schema for updating a report definition."""

    name: str | None = Field(None, description="Report name", min_length=1, max_length=255)
    description: str | None = Field(None, description="Report description")
    filters: dict[str, Any] | None = Field(None, description="Filter configuration")
    config: dict[str, Any] | None = Field(
        None, description="Visualization-specific configuration"
    )


class ReportDefinitionResponse(BaseModel):
    """Schema for report definition response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    data_source_type: str
    filters: dict[str, Any] | None
    visualization_type: str
    config: dict[str, Any] | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class ReportExecutionRequest(BaseModel):
    """Schema for executing a report."""

    filters: dict[str, Any] | None = Field(None, description="Additional filters")
    pagination: dict[str, int] | None = Field(
        None, description="Pagination configuration (skip, limit)"
    )


class ReportExecutionResponse(BaseModel):
    """Schema for report execution response."""

    data: list[dict[str, Any]] = Field(..., description="Report data")
    total: int = Field(..., description="Total number of records")
    visualization: dict[str, Any] = Field(..., description="Visualization data")
    columns: list[dict[str, Any]] = Field(..., description="Available columns")









