"""Authentication schemas for login, tokens, and user info."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Schema for login request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""

    refresh_token: str = Field(..., description="Refresh token to exchange for new access token")


class TokenResponse(BaseModel):
    """Schema for token response after successful login."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    refresh_token: str = Field(..., description="JWT refresh token")


class AccessTokenResponse(BaseModel):
    """Schema for access token response after refresh."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class UserMeResponse(BaseModel):
    """Schema for /me endpoint response with user info and permissions."""

    id: UUID
    email: str
    full_name: str | None
    tenant_id: UUID = Field(..., description="Tenant ID for multi-tenancy isolation")
    roles: list[str] = Field(default_factory=list, description="Global roles assigned to the user")
    permissions: list[str] = Field(default_factory=list, description="Effective permissions (from roles, module roles, and delegated permissions)")

    model_config = ConfigDict(from_attributes=True)


class RoleAssignRequest(BaseModel):
    """Schema for assigning a global role to a user."""

    role: str = Field(..., description="Role name (owner, admin, manager, staff, viewer)")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate that role is a valid global role."""
        valid_roles = {"owner", "admin", "manager", "staff", "viewer"}
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v


class RoleResponse(BaseModel):
    """Schema for role response."""

    role: str
    granted_by: UUID | None = Field(None, description="ID of the user who granted this role. None if granted by system.")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleListResponse(BaseModel):
    """Schema for list of roles."""

    roles: list[RoleResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total number of roles")
