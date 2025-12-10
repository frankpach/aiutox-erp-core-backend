"""Contact method schemas for API requests and responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ContactMethodBase(BaseModel):
    """Base contact method schema with common fields."""

    method_type: str = Field(..., description="Method type: email, phone, mobile, whatsapp, etc.")
    value: str = Field(..., description="Contact value")
    label: str | None = Field(None, description="Custom label (e.g., 'Trabajo', 'Personal')")
    is_primary: bool = Field(False, description="Primary contact method")
    is_verified: bool = Field(False, description="Verified contact method")
    notes: str | None = Field(None, description="Notes")


class ContactMethodAddressFields(BaseModel):
    """Address fields for address-type contact methods."""

    address_line1: str | None = Field(None, description="Address line 1")
    address_line2: str | None = Field(None, description="Address line 2")
    city: str | None = Field(None, description="City")
    state_province: str | None = Field(None, description="State/Province")
    postal_code: str | None = Field(None, description="Postal code")
    country: str | None = Field(None, description="Country (ISO 3166-1 alpha-2)")


class ContactMethodCreate(ContactMethodBase, ContactMethodAddressFields):
    """Schema for creating a new contact method."""

    entity_type: str = Field(..., description="Entity type: user, contact, organization, etc.")
    entity_id: UUID = Field(..., description="Entity ID")

    @field_validator("address_line1", "city", "country")
    @classmethod
    def validate_address_fields(cls, v, info):
        """Validate address fields are provided when method_type is address."""
        if info.data.get("method_type") == "address":
            if not v:
                raise ValueError("Address fields are required when method_type is 'address'")
        return v


class ContactMethodUpdate(BaseModel):
    """Schema for updating a contact method."""

    value: str | None = None
    label: str | None = None
    is_primary: bool | None = None
    is_verified: bool | None = None
    verified_at: datetime | None = None
    notes: str | None = None
    # Address fields
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state_province: str | None = None
    postal_code: str | None = None
    country: str | None = None


class ContactMethodResponse(ContactMethodBase, ContactMethodAddressFields):
    """Schema for contact method response."""

    id: UUID
    entity_type: str
    entity_id: UUID
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
