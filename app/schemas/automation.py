"""Automation schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TriggerSchema(BaseModel):
    """Trigger schema for automation rules."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"type": "event", "event_type": "product.created"}
        }
    )

    type: str = Field(..., description="Trigger type: 'event' or 'time'")
    event_type: str | None = Field(None, description="Event type (for event triggers)")
    schedule: dict[str, Any] | None = Field(None, description="Schedule config (for time triggers)")


class ConditionSchema(BaseModel):
    """Condition schema for automation rules."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"field": "metadata.stock.quantity", "operator": "<", "value": 10}
        }
    )

    field: str = Field(..., description="Field path (e.g., 'metadata.stock.quantity')")
    operator: str = Field(
        ..., description="Comparison operator: ==, !=, >, <, >=, <=, in, contains"
    )
    value: Any = Field(..., description="Value to compare against")


class ActionSchema(BaseModel):
    """Action schema for automation rules."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "notification",
                "template": "low_stock_alert",
                "recipients": ["admin@tenant.com"],
            }
        }
    )

    type: str = Field(..., description="Action type: 'notification', 'create_activity', 'invoke_api'")
    template: str | None = Field(None, description="Template name (for notification actions)")
    recipients: list[str] | None = Field(None, description="Recipients (for notification actions)")
    activity_type: str | None = Field(None, description="Activity type (for create_activity)")
    description: str | None = Field(None, description="Description (for create_activity)")
    url: str | None = Field(None, description="URL (for invoke_api)")
    method: str | None = Field(None, description="HTTP method (for invoke_api)")
    headers: dict[str, str] | None = Field(None, description="Headers (for invoke_api)")
    body: dict[str, Any] | None = Field(None, description="Request body (for invoke_api)")


class RuleBase(BaseModel):
    """Base schema for automation rules."""

    name: str = Field(..., description="Rule name", min_length=1, max_length=255)
    description: str | None = Field(None, description="Rule description")
    enabled: bool = Field(default=True, description="Whether rule is enabled")
    trigger: TriggerSchema = Field(..., description="Trigger configuration")
    conditions: list[ConditionSchema] | None = Field(
        default=None, description="List of conditions (optional)"
    )
    actions: list[ActionSchema] = Field(..., description="List of actions to execute", min_length=1)


class RuleCreate(RuleBase):
    """Schema for creating a rule."""

    pass


class RuleUpdate(BaseModel):
    """Schema for updating a rule."""

    name: str | None = Field(None, description="Rule name", min_length=1, max_length=255)
    description: str | None = Field(None, description="Rule description")
    enabled: bool | None = Field(None, description="Whether rule is enabled")
    trigger: TriggerSchema | None = Field(None, description="Trigger configuration")
    conditions: list[ConditionSchema] | None = Field(
        None, description="List of conditions (optional)"
    )
    actions: list[ActionSchema] | None = Field(None, description="List of actions to execute")


class RuleResponse(BaseModel):
    """Schema for rule response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    enabled: bool
    trigger: dict[str, Any]
    conditions: list[dict[str, Any]] | None
    actions: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class AutomationExecutionResponse(BaseModel):
    """Schema for automation execution response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_id: UUID
    event_id: UUID | None
    status: str
    result: dict[str, Any] | None
    error_message: str | None
    executed_at: str










