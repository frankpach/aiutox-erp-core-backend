"""Notification schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationTemplateBase(BaseModel):
    """Base schema for notification templates."""

    name: str = Field(..., description="Template name", min_length=1, max_length=255)
    event_type: str = Field(..., description="Event type (e.g., 'product.created')", max_length=100)
    channel: str = Field(..., description="Channel: 'email', 'sms', 'webhook', 'in-app'", max_length=50)
    subject: str | None = Field(None, description="Email subject (for email channel)", max_length=500)
    body: str = Field(..., description="Template body with {{variables}}")
    is_active: bool = Field(default=True, description="Whether template is active")


class NotificationTemplateCreate(NotificationTemplateBase):
    """Schema for creating a notification template."""

    pass


class NotificationTemplateUpdate(BaseModel):
    """Schema for updating a notification template."""

    name: str | None = Field(None, description="Template name", min_length=1, max_length=255)
    event_type: str | None = Field(None, description="Event type", max_length=100)
    channel: str | None = Field(None, description="Channel", max_length=50)
    subject: str | None = Field(None, description="Email subject", max_length=500)
    body: str | None = Field(None, description="Template body")
    is_active: bool | None = Field(None, description="Whether template is active")


class NotificationTemplateResponse(NotificationTemplateBase):
    """Schema for notification template response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationSendRequest(BaseModel):
    """Schema for sending a notification manually."""

    event_type: str = Field(..., description="Event type that triggered the notification")
    recipient_id: UUID = Field(..., description="User ID to send notification to")
    channels: list[str] = Field(..., description="List of channels", min_length=1)
    data: dict[str, Any] | None = Field(None, description="Event data for template rendering")


class NotificationQueueResponse(BaseModel):
    """Schema for notification queue entry response."""

    id: UUID
    event_type: str
    recipient_id: UUID
    tenant_id: UUID
    channel: str
    template_id: UUID | None
    data: dict[str, Any] | None
    status: str
    sent_at: datetime | None
    error_message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationQueueListResponse(BaseModel):
    """Schema for list of notification queue entries."""

    items: list[NotificationQueueResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

