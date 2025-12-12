"""Contact schemas for API requests and responses."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.schemas.contact_method import ContactMethodResponse
    from app.schemas.organization import OrganizationResponse


class ContactBase(BaseModel):
    """Base contact schema with common fields."""

    first_name: str | None = Field(None, description="First name")
    last_name: str | None = Field(None, description="Last name")
    middle_name: str | None = Field(None, description="Middle name")
    full_name: str | None = Field(None, description="Full name")
    job_title: str | None = Field(None, description="Job title in organization")
    department: str | None = Field(None, description="Department")
    is_primary_contact: bool = Field(False, description="Primary contact of organization")
    notes: str | None = Field(None, description="Notes")


class ContactCreate(ContactBase):
    """Schema for creating a new contact."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    organization_id: UUID | None = Field(None, description="Organization ID (optional)")


class ContactUpdate(BaseModel):
    """Schema for updating a contact."""

    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    full_name: str | None = None
    job_title: str | None = None
    department: str | None = None
    is_primary_contact: bool | None = None
    organization_id: UUID | None = None
    notes: str | None = None
    is_active: bool | None = None


class ContactResponse(ContactBase):
    """Schema for contact response."""

    id: UUID
    tenant_id: UUID
    organization_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    organization: "OrganizationResponse | None" = Field(None, description="Associated organization")
    contact_methods: list["ContactMethodResponse"] = Field(
        default_factory=list, description="Contact methods"
    )

    model_config = ConfigDict(from_attributes=True)
