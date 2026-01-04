from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PipelineBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    is_default: bool = False


class PipelineCreate(PipelineBase):
    pass


class PipelineUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    is_default: bool | None = None


class PipelineResponse(PipelineBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class LeadBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    status: str = Field(default="new", max_length=50)
    source: str | None = Field(None, max_length=100)
    pipeline_id: UUID | None = None
    organization_id: UUID | None = None
    contact_id: UUID | None = None
    assigned_to_id: UUID | None = None
    next_event_id: UUID | None = None
    estimated_value: Decimal | None = None
    probability: Decimal | None = None
    notes: str | None = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    status: str | None = Field(None, max_length=50)
    source: str | None = Field(None, max_length=100)
    pipeline_id: UUID | None = None
    organization_id: UUID | None = None
    contact_id: UUID | None = None
    assigned_to_id: UUID | None = None
    next_event_id: UUID | None = None
    estimated_value: Decimal | None = None
    probability: Decimal | None = None
    notes: str | None = None


class LeadResponse(LeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_by_id: UUID | None
    created_at: datetime
    updated_at: datetime


class OpportunityBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    stage: str | None = Field(None, max_length=100)
    status: str = Field(default="open", max_length=50)
    pipeline_id: UUID | None = None
    organization_id: UUID | None = None
    contact_id: UUID | None = None
    assigned_to_id: UUID | None = None
    next_event_id: UUID | None = None
    amount: Decimal | None = None
    probability: Decimal | None = None
    expected_close_date: datetime | None = None
    notes: str | None = None


class OpportunityCreate(OpportunityBase):
    pass


class OpportunityUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    stage: str | None = Field(None, max_length=100)
    status: str | None = Field(None, max_length=50)
    pipeline_id: UUID | None = None
    organization_id: UUID | None = None
    contact_id: UUID | None = None
    assigned_to_id: UUID | None = None
    next_event_id: UUID | None = None
    amount: Decimal | None = None
    probability: Decimal | None = None
    expected_close_date: datetime | None = None
    notes: str | None = None


class OpportunityResponse(OpportunityBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_by_id: UUID | None
    created_at: datetime
    updated_at: datetime
