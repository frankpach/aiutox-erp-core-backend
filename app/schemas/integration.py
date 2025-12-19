"""Integration schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.integration import IntegrationStatus, IntegrationType, WebhookStatus


class IntegrationBase(BaseModel):
    """Base schema for integration."""

    name: str = Field(..., description="Integration name", max_length=255)
    description: str | None = Field(None, description="Integration description")
    integration_type: str = Field(..., description="Integration type")
    config: dict[str, Any] = Field(..., description="Integration configuration")
    credentials: dict[str, Any] | None = Field(None, description="Integration credentials")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class IntegrationCreate(IntegrationBase):
    """Schema for creating an integration."""

    pass


class IntegrationUpdate(BaseModel):
    """Schema for updating an integration."""

    name: str | None = Field(None, description="Integration name", max_length=255)
    description: str | None = Field(None, description="Integration description")
    status: str | None = Field(None, description="Integration status")
    config: dict[str, Any] | None = Field(None, description="Integration configuration")
    credentials: dict[str, Any] | None = Field(None, description="Integration credentials")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class IntegrationResponse(BaseModel):
    """Schema for integration response."""

    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    integration_type: str
    status: str
    config: dict[str, Any]
    metadata: dict[str, Any] | None = Field(None, alias="integration_metadata", description="Additional metadata")
    created_at: datetime
    updated_at: datetime
    last_sync_at: datetime | None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class WebhookBase(BaseModel):
    """Base schema for webhook."""

    name: str = Field(..., description="Webhook name", max_length=255)
    url: str = Field(..., description="Webhook URL", max_length=1000)
    event_type: str = Field(..., description="Event type", max_length=100)
    enabled: bool = Field(default=True, description="Whether webhook is enabled")
    method: str = Field(default="POST", description="HTTP method")
    headers: dict[str, str] | None = Field(None, description="Custom headers")
    secret: str | None = Field(None, description="Secret for signature validation", max_length=255)
    max_retries: int = Field(default=3, ge=0, description="Maximum number of retries")
    retry_delay: int = Field(default=60, ge=1, description="Retry delay in seconds")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class WebhookCreate(WebhookBase):
    """Schema for creating a webhook."""

    integration_id: UUID | None = Field(None, description="Integration ID")


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook."""

    name: str | None = Field(None, description="Webhook name", max_length=255)
    url: str | None = Field(None, description="Webhook URL", max_length=1000)
    event_type: str | None = Field(None, description="Event type", max_length=100)
    enabled: bool | None = Field(None, description="Whether webhook is enabled")
    method: str | None = Field(None, description="HTTP method")
    headers: dict[str, str] | None = Field(None, description="Custom headers")
    secret: str | None = Field(None, description="Secret for signature validation", max_length=255)
    max_retries: int | None = Field(None, ge=0, description="Maximum number of retries")
    retry_delay: int | None = Field(None, ge=1, description="Retry delay in seconds")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class WebhookResponse(WebhookBase):
    """Schema for webhook response."""

    id: UUID
    tenant_id: UUID
    integration_id: UUID | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] | None = Field(None, alias="webhook_metadata", description="Additional metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class WebhookDeliveryResponse(BaseModel):
    """Schema for webhook delivery response."""

    id: UUID
    webhook_id: UUID
    tenant_id: UUID
    status: str
    event_type: str
    payload: dict[str, Any]
    response_status: int | None
    response_body: str | None
    error_message: str | None
    retry_count: int
    next_retry_at: datetime | None
    created_at: datetime
    sent_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class IntegrationLogResponse(BaseModel):
    """Schema for integration log response."""

    id: UUID
    integration_id: UUID | None
    tenant_id: UUID
    action: str
    status: str
    message: str | None
    data: dict[str, Any] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)








