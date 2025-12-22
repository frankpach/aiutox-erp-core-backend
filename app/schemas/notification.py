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


# Channel Configuration Schemas
class SMTPConfigRequest(BaseModel):
    """Schema for SMTP channel configuration."""

    enabled: bool = Field(default=True, description="Whether SMTP channel is enabled")
    host: str = Field(..., description="SMTP server host", max_length=255)
    port: int = Field(..., description="SMTP server port", ge=1, le=65535)
    user: str = Field(..., description="SMTP username", max_length=255)
    password: str = Field(..., description="SMTP password", max_length=255)
    use_tls: bool = Field(default=True, description="Use TLS encryption")
    from_email: str = Field(..., description="Default sender email", max_length=255)
    from_name: str | None = Field(None, description="Default sender name", max_length=255)


class SMTPConfigResponse(BaseModel):
    """Schema for SMTP channel configuration response."""

    enabled: bool
    host: str
    port: int
    user: str
    password: str | None = Field(None, description="Password is hidden in response")
    use_tls: bool
    from_email: str
    from_name: str | None


class SMSConfigRequest(BaseModel):
    """Schema for SMS channel configuration."""

    enabled: bool = Field(default=False, description="Whether SMS channel is enabled")
    provider: str = Field(default="twilio", description="SMS provider", max_length=50)
    account_sid: str | None = Field(None, description="Provider account SID", max_length=255)
    auth_token: str | None = Field(None, description="Provider auth token", max_length=255)
    from_number: str | None = Field(None, description="Default sender number", max_length=20)


class SMSConfigResponse(BaseModel):
    """Schema for SMS channel configuration response."""

    enabled: bool
    provider: str
    account_sid: str | None
    auth_token: str | None = Field(None, description="Auth token is hidden in response")
    from_number: str | None


class WebhookConfigRequest(BaseModel):
    """Schema for webhook channel configuration."""

    enabled: bool = Field(default=False, description="Whether webhook channel is enabled")
    url: str = Field(..., description="Webhook URL", max_length=500)
    secret: str | None = Field(None, description="Webhook secret for signing", max_length=255)
    timeout: int = Field(default=30, description="Request timeout in seconds", ge=1, le=300)


class WebhookConfigResponse(BaseModel):
    """Schema for webhook channel configuration response."""

    enabled: bool
    url: str
    secret: str | None = Field(None, description="Secret is hidden in response")
    timeout: int


class NotificationChannelsResponse(BaseModel):
    """Schema for all notification channels configuration."""

    smtp: SMTPConfigResponse
    sms: SMSConfigResponse
    webhook: WebhookConfigResponse
