"""Approval schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Approval Flow schemas
class ApprovalFlowBase(BaseModel):
    """Base schema for approval flow."""

    name: str = Field(..., description="Flow name", max_length=255)
    description: str | None = Field(None, description="Flow description")
    flow_type: str = Field(..., description="Flow type (sequential, parallel, conditional)", max_length=20)
    module: str = Field(..., description="Module name (e.g., 'products', 'orders')", max_length=50)
    conditions: dict[str, Any] | None = Field(None, description="Conditional rules for flow")
    is_active: bool = Field(True, description="Whether flow is active")


class ApprovalFlowCreate(ApprovalFlowBase):
    """Schema for creating an approval flow."""

    pass


class ApprovalFlowUpdate(BaseModel):
    """Schema for updating an approval flow."""

    name: str | None = Field(None, description="Flow name", max_length=255)
    description: str | None = Field(None, description="Flow description")
    flow_type: str | None = Field(None, description="Flow type", max_length=20)
    conditions: dict[str, Any] | None = Field(None, description="Conditional rules")
    is_active: bool | None = Field(None, description="Whether flow is active")


class ApprovalFlowResponse(ApprovalFlowBase):
    """Schema for approval flow response."""

    id: UUID
    tenant_id: UUID
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Approval Step schemas
class ApprovalStepBase(BaseModel):
    """Base schema for approval step."""

    flow_id: UUID = Field(..., description="Flow ID")
    step_order: int = Field(..., description="Step order in flow")
    name: str = Field(..., description="Step name", max_length=255)
    description: str | None = Field(None, description="Step description")
    approver_type: str = Field(..., description="Approver type (user, role, dynamic)", max_length=20)
    approver_id: UUID | None = Field(None, description="Approver user/role ID")
    approver_role: str | None = Field(None, description="Approver role name", max_length=50)
    approver_rule: dict[str, Any] | None = Field(None, description="Dynamic approver rule")
    require_all: bool = Field(False, description="Require all approvers (for parallel)")
    min_approvals: int | None = Field(None, description="Minimum approvals required")


class ApprovalStepCreate(ApprovalStepBase):
    """Schema for creating an approval step."""

    pass


class ApprovalStepUpdate(BaseModel):
    """Schema for updating an approval step."""

    step_order: int | None = Field(None, description="Step order")
    name: str | None = Field(None, description="Step name", max_length=255)
    description: str | None = Field(None, description="Step description")
    approver_type: str | None = Field(None, description="Approver type", max_length=20)
    approver_id: UUID | None = Field(None, description="Approver user/role ID")
    approver_role: str | None = Field(None, description="Approver role name", max_length=50)
    approver_rule: dict[str, Any] | None = Field(None, description="Dynamic approver rule")
    require_all: bool | None = Field(None, description="Require all approvers")
    min_approvals: int | None = Field(None, description="Minimum approvals required")


class ApprovalStepResponse(ApprovalStepBase):
    """Schema for approval step response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Approval Request schemas
class ApprovalRequestBase(BaseModel):
    """Base schema for approval request."""

    flow_id: UUID = Field(..., description="Flow ID")
    title: str = Field(..., description="Request title", max_length=255)
    description: str | None = Field(None, description="Request description")
    entity_type: str = Field(..., description="Entity type (e.g., 'order', 'invoice')", max_length=50)
    entity_id: UUID = Field(..., description="Entity ID")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class ApprovalRequestCreate(ApprovalRequestBase):
    """Schema for creating an approval request."""

    pass


class ApprovalRequestResponse(ApprovalRequestBase):
    """Schema for approval request response."""

    id: UUID
    tenant_id: UUID
    status: str
    current_step: int
    requested_by: UUID | None
    requested_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Approval Action schemas
class ApprovalActionBase(BaseModel):
    """Base schema for approval action."""

    request_id: UUID = Field(..., description="Request ID")
    action_type: str = Field(..., description="Action type (approve, reject, delegate, comment)", max_length=20)
    step_order: int = Field(..., description="Step order")
    comment: str | None = Field(None, description="Optional comment")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class ApprovalActionCreate(ApprovalActionBase):
    """Schema for creating an approval action."""

    pass


class ApprovalActionResponse(ApprovalActionBase):
    """Schema for approval action response."""

    id: UUID
    tenant_id: UUID
    acted_by: UUID | None
    acted_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Approval Delegation schemas
class ApprovalDelegationBase(BaseModel):
    """Base schema for approval delegation."""

    request_id: UUID = Field(..., description="Request ID")
    from_user_id: UUID = Field(..., description="User delegating approval")
    to_user_id: UUID = Field(..., description="User receiving delegation")
    reason: str | None = Field(None, description="Delegation reason")
    expires_at: datetime | None = Field(None, description="Delegation expiration")


class ApprovalDelegationCreate(ApprovalDelegationBase):
    """Schema for creating an approval delegation."""

    pass


class ApprovalDelegationResponse(ApprovalDelegationBase):
    """Schema for approval delegation response."""

    id: UUID
    tenant_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

