"""Organization schemas for API requests and responses."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
# MOVED TO LOCAL IMPORT:     from app.schemas.contact import ContactResponse
    from app.schemas.contact_method import ContactMethodResponse


class OrganizationBase(BaseModel):
    """Base organization schema with common fields."""

    name: str = Field(..., description="Organization name")
    legal_name: str | None = Field(None, description="Legal name (razón social)")
    tax_id: str | None = Field(None, description="Tax ID (NIT, RUC, etc.)")
    organization_type: str = Field(..., description="Type: customer, supplier, partner, other")
    industry: str | None = Field(None, description="Industry/sector")
    website: str | None = Field(None, description="Website URL")
    logo_url: str | None = Field(None, description="Logo URL")
    notes: str | None = Field(None, description="Internal notes")


class OrganizationCreate(OrganizationBase):
    """Schema for creating a new organization."""

    tenant_id: UUID = Field(..., description="Tenant ID")


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization."""

    name: str | None = None
    legal_name: str | None = None
    tax_id: str | None = None
    organization_type: str | None = None
    industry: str | None = None
    website: str | None = None
    logo_url: str | None = None
    is_active: bool | None = None
    notes: str | None = None


class OrganizationResponse(OrganizationBase):
    """Schema for organization response."""

    id: UUID
    tenant_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    contacts: list["ContactResponse"] = Field(default_factory=list, description="Organization contacts")
    contact_methods: list["ContactMethodResponse"] = Field(
        default_factory=list, description="Organization contact methods"
    )

    model_config = ConfigDict(from_attributes=True)

