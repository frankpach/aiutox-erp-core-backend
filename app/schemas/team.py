"""Team schemas for API requests and responses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TeamBase(BaseModel):
    """Base schema for team."""

    name: str = Field(..., description="Team name", max_length=255)
    description: str | None = Field(None, description="Team description")
    parent_team_id: UUID | None = Field(None, description="Parent team ID for hierarchy")
    color: str | None = Field(None, description="Hex color code", max_length=7)
    is_active: bool = Field(default=True, description="Whether team is active")


class TeamCreate(TeamBase):
    """Schema for creating a team."""

    pass


class TeamUpdate(BaseModel):
    """Schema for updating a team."""

    name: str | None = Field(None, description="Team name", max_length=255)
    description: str | None = Field(None, description="Team description")
    parent_team_id: UUID | None = Field(None, description="Parent team ID")
    color: str | None = Field(None, description="Hex color code", max_length=7)
    is_active: bool | None = Field(None, description="Whether team is active")


class TeamResponse(TeamBase):
    """Schema for team response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TeamMemberBase(BaseModel):
    """Base schema for team member."""

    team_id: UUID = Field(..., description="Team ID")
    user_id: UUID = Field(..., description="User ID")
    role: str | None = Field(None, description="Member role (e.g., 'member', 'leader', 'admin')")


class TeamMemberCreate(TeamMemberBase):
    """Schema for creating a team member."""

    pass


class TeamMemberResponse(TeamMemberBase):
    """Schema for team member response."""

    id: UUID
    tenant_id: UUID
    added_by: UUID | None
    added_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
