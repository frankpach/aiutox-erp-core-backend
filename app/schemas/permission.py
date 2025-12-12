"""Schemas for delegated permission management."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DelegatedPermissionCreate(BaseModel):
    """Schema for creating a delegated permission."""

    user_id: UUID = Field(..., description="ID of the user receiving the permission")
    module: str = Field(..., min_length=1, max_length=100, description="Module name (e.g., 'inventory', 'products')")
    permission: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Permission string (e.g., 'inventory.edit', 'products.view')",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Expiration date for the permission. If None, permission does not expire.",
    )

    @field_validator("permission")
    @classmethod
    def validate_permission_format(cls, v: str) -> str:
        """
        Validate permission format: must be 'module.action'.

        Args:
            v: Permission string to validate.

        Returns:
            Validated permission string.

        Raises:
            ValueError: If permission format is invalid.
        """
        parts = v.split(".")
        if len(parts) != 2:
            raise ValueError("Permission must be in format 'module.action' (e.g., 'inventory.edit')")
        return v

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v: datetime | None) -> datetime | None:
        """
        Validate that expires_at is in the future if provided.

        Args:
            v: Expiration datetime or None.

        Returns:
            Validated expiration datetime or None.

        Raises:
            ValueError: If expires_at is in the past.
        """
        if v is not None:
            from datetime import timezone

            now = datetime.now(timezone.utc) if v.tzinfo else datetime.now()
            if v <= now:
                raise ValueError("expires_at must be in the future")
        return v


class DelegatedPermissionResponse(BaseModel):
    """Schema for delegated permission response."""

    id: UUID
    user_id: UUID
    granted_by: UUID
    module: str
    permission: str
    expires_at: datetime | None
    created_at: datetime
    revoked_at: datetime | None
    is_active: bool = Field(..., description="Whether the permission is currently active")

    model_config = ConfigDict(from_attributes=True)


class DelegatedPermissionListResponse(BaseModel):
    """Schema for list of delegated permissions."""

    permissions: list[DelegatedPermissionResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total number of permissions")


class RevokePermissionResponse(BaseModel):
    """Schema for permission revocation response."""

    message: str = Field(..., description="Success message")
    revoked_count: int = Field(default=1, description="Number of permissions revoked")


class PermissionGrantRequest(BaseModel):
    """Schema for granting a permission (used in endpoint body)."""

    user_id: UUID = Field(..., description="ID of the user receiving the permission")
    permission: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Permission string (e.g., 'inventory.edit', 'products.view')",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Expiration date for the permission. If None, permission does not expire.",
    )

    @field_validator("permission")
    @classmethod
    def validate_permission_format(cls, v: str) -> str:
        """
        Validate permission format: must be 'module.action'.

        Args:
            v: Permission string to validate.

        Returns:
            Validated permission string.

        Raises:
            ValueError: If permission format is invalid.
        """
        parts = v.split(".")
        if len(parts) != 2:
            raise ValueError("Permission must be in format 'module.action' (e.g., 'inventory.edit')")
        return v

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v: datetime | None) -> datetime | None:
        """
        Validate that expires_at is in the future if provided.

        Args:
            v: Expiration datetime or None.

        Returns:
            Validated expiration datetime or None.

        Raises:
            ValueError: If expires_at is in the past.
        """
        if v is not None:
            from datetime import timezone

            now = datetime.now(timezone.utc) if v.tzinfo else datetime.now()
            if v <= now:
                raise ValueError("expires_at must be in the future")
        return v

