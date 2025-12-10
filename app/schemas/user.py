"""User schemas for API requests and responses."""

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

if TYPE_CHECKING:
    from app.schemas.contact_method import ContactMethodResponse


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=8, description="User password (minimum 8 characters)")
    tenant_id: UUID = Field(..., description="Tenant ID")
    # Información personal (opcional)
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    nationality: str | None = None
    marital_status: str | None = None
    # Información laboral (opcional)
    job_title: str | None = None
    department: str | None = None
    employee_id: str | None = None
    # Preferencias (opcional)
    preferred_language: str = Field(default="es", description="Preferred language")
    timezone: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    notes: str | None = None


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    full_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    nationality: str | None = None
    marital_status: str | None = None
    job_title: str | None = None
    department: str | None = None
    employee_id: str | None = None
    preferred_language: str | None = None
    timezone: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    notes: str | None = None
    is_active: bool | None = None
    two_factor_enabled: bool | None = None


class UserResponse(UserBase):
    """Schema for user response."""

    id: UUID
    tenant_id: UUID
    # Información personal
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    nationality: str | None = None
    marital_status: str | None = None
    # Información laboral
    job_title: str | None = None
    department: str | None = None
    employee_id: str | None = None
    # Preferencias
    preferred_language: str = "es"
    timezone: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    notes: str | None = None
    # Autenticación
    last_login_at: datetime | None = None
    email_verified_at: datetime | None = None
    phone_verified_at: datetime | None = None
    two_factor_enabled: bool = False
    is_active: bool
    created_at: datetime
    updated_at: datetime
    contact_methods: list["ContactMethodResponse"] = Field(
        default_factory=list, description="User contact methods"
    )

    class Config:
        from_attributes = True

