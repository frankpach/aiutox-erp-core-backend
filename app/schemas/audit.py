"""Pydantic schemas for audit log responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    """Response schema for a single audit log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Audit log entry ID")
    user_id: UUID | None = Field(None, description="User who performed the action")
    tenant_id: UUID = Field(..., description="Tenant ID")
    action: str = Field(..., description="Action type (e.g., 'grant_permission', 'create_user')")
    resource_type: str | None = Field(None, description="Type of resource affected")
    resource_id: UUID | None = Field(None, description="ID of the resource affected")
    details: dict[str, Any] | None = Field(None, description="Additional details as JSON")
    ip_address: str | None = Field(None, description="Client IP address")
    user_agent: str | None = Field(None, description="Client user agent")
    created_at: datetime = Field(..., description="Timestamp when the action occurred")


class AuditLogListResponse(BaseModel):
    """Response schema for a list of audit logs with pagination."""

    data: list[AuditLogResponse] = Field(..., description="List of audit log entries")
    meta: dict[str, Any] = Field(
        ...,
        description="Pagination metadata",
        json_schema_extra={
            "example": {
                "total": 100,
                "page": 1,
                "page_size": 20,
                "total_pages": 5,
            }
        },
    )

