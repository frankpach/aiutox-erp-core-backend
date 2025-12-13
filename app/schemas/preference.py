"""Preference schemas for API requests and responses."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PreferenceValue(BaseModel):
    """Preference value schema."""

    key: str = Field(..., description="Preference key")
    value: Any = Field(..., description="Preference value")


class PreferenceSetRequest(BaseModel):
    """Schema for setting preferences."""

    preferences: dict[str, Any] = Field(..., description="Dictionary of preference key-value pairs")


class NotificationPreferenceSchema(BaseModel):
    """Schema for notification preferences."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "enabled": True,
                "channels": ["email", "in-app"],
                "frequency": "immediate",
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "08:00",
            }
        }
    )

    enabled: bool = Field(default=True, description="Whether notifications are enabled")
    channels: list[str] = Field(
        default=["in-app"], description="Notification channels: email, in-app, sms"
    )
    frequency: str = Field(
        default="immediate", description="Frequency: immediate, daily, weekly"
    )
    quiet_hours_start: str | None = Field(
        None, description="Start of quiet hours (HH:MM format)"
    )
    quiet_hours_end: str | None = Field(
        None, description="End of quiet hours (HH:MM format)"
    )


class NotificationPreferencesRequest(BaseModel):
    """Schema for setting notification preferences by event type."""

    preferences: dict[str, NotificationPreferenceSchema] = Field(
        ..., description="Notification preferences by event type"
    )


class SavedViewCreate(BaseModel):
    """Schema for creating a saved view."""

    name: str = Field(..., description="View name", min_length=1, max_length=255)
    config: dict[str, Any] = Field(..., description="View configuration")
    is_default: bool = Field(default=False, description="Whether this is the default view")


class SavedViewUpdate(BaseModel):
    """Schema for updating a saved view."""

    name: str | None = Field(None, description="View name", min_length=1, max_length=255)
    config: dict[str, Any] | None = Field(None, description="View configuration")
    is_default: bool | None = Field(None, description="Whether this is the default view")


class SavedViewResponse(BaseModel):
    """Schema for saved view response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    tenant_id: UUID
    module: str
    name: str
    config: dict[str, Any]
    is_default: bool
    created_at: str
    updated_at: str


class DashboardCreate(BaseModel):
    """Schema for creating a dashboard."""

    name: str = Field(..., description="Dashboard name", min_length=1, max_length=255)
    widgets: list[dict[str, Any]] = Field(..., description="List of widget configurations")
    is_default: bool = Field(default=False, description="Whether this is the default dashboard")


class DashboardUpdate(BaseModel):
    """Schema for updating a dashboard."""

    name: str | None = Field(None, description="Dashboard name", min_length=1, max_length=255)
    widgets: list[dict[str, Any]] | None = Field(
        None, description="List of widget configurations"
    )
    is_default: bool | None = Field(None, description="Whether this is the default dashboard")


class DashboardResponse(BaseModel):
    """Schema for dashboard response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    tenant_id: UUID
    name: str
    widgets: list[dict[str, Any]]
    is_default: bool
    created_at: str
    updated_at: str



