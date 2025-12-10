"""Tenant schemas for API requests and responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TenantBase(BaseModel):
    """Base tenant schema with common fields."""

    name: str = Field(..., description="Tenant name")
    slug: str = Field(..., description="Unique slug identifier")


class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""

    pass


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""

    name: str | None = None
    slug: str | None = None


class TenantResponse(TenantBase):
    """Schema for tenant response."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

