"""Integration schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IntegrationBase(BaseModel):
    """Base schema for integration."""

    name: str = Field(..., description="Integration name", max_length=255)
    type: str = Field(..., description="Integration type", max_length=50)
    config: dict[str, Any] = Field(..., description="Integration configuration (credentials, settings)")


class IntegrationCreate(IntegrationBase):
    """Schema for creating an integration."""

    pass


class WebhookCreate(BaseModel):
    """Schema for creating a webhook integration."""

    name: str = Field(..., description="Webhook name", max_length=255)
    url: str = Field(..., description="Webhook URL", max_length=500)
    event_type: str = Field(..., description="Event type (e.g., 'product.created')", max_length=100)


class WebhookResponse(BaseModel):
    """Schema for webhook response."""

    id: UUID
    tenant_id: UUID
    name: str
    type: str
    event_type: str
    url: str
    enabled: bool
    status: str
    last_sync_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IntegrationUpdate(BaseModel):
    """Schema for updating an integration."""

    name: str | None = Field(None, description="Integration name", max_length=255)
    config: dict[str, Any] | None = Field(None, description="Integration configuration")
    status: str | None = Field(None, description="Integration status")


class IntegrationResponse(IntegrationBase):
    """Schema for integration response."""

    id: UUID
    tenant_id: UUID
    status: str
    last_sync_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IntegrationActivateRequest(BaseModel):
    """Schema for activating an integration."""

    config: dict[str, Any] = Field(..., description="Integration configuration")


class IntegrationTestResponse(BaseModel):
    """Schema for integration test response."""

    success: bool
    message: str
    details: dict[str, Any] | None = None


class IntegrationLogResponse(BaseModel):
    """Schema for integration log response."""

    id: UUID
    integration_id: UUID
    tenant_id: UUID
    level: str
    message: str
    details: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IntegrationCredentialsResponse(BaseModel):
    """Schema for integration credentials response."""

    credentials: dict[str, Any] = Field(..., description="Decrypted credentials")
