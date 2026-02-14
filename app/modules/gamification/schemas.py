"""Pydantic v2 schemas for gamification module."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserPointsResponse(BaseModel):
    """Response schema for user points."""

    id: UUID
    user_id: UUID
    total_points: int
    level: int
    current_streak: int
    longest_streak: int
    last_activity_date: str | None = None
    progress_to_next_level: float = Field(
        0.0, description="Percentage progress to next level (0-100)"
    )
    points_to_next_level: int = Field(
        0, description="Points needed to reach next level"
    )
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GamificationEventResponse(BaseModel):
    """Response schema for gamification events (points history)."""

    id: UUID
    event_type: str
    source_module: str
    source_id: UUID | None = None
    points_earned: int
    metadata: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BadgeResponse(BaseModel):
    """Response schema for badge definitions."""

    id: UUID
    name: str
    description: str | None = None
    icon: str
    criteria: dict[str, Any]
    points_value: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserBadgeResponse(BaseModel):
    """Response schema for user badges."""

    id: UUID
    badge_id: UUID
    badge_name: str = ""
    badge_description: str | None = None
    badge_icon: str = "trophy"
    earned_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeaderboardEntryResponse(BaseModel):
    """Response schema for leaderboard entries."""

    rank: int | None = None
    user_id: UUID
    user_name: str = ""
    points: int
    is_current_user: bool = False

    model_config = ConfigDict(from_attributes=True)


class BadgeCreate(BaseModel):
    """Schema for creating a badge (admin only)."""

    name: str = Field(..., max_length=100)
    description: str | None = None
    icon: str = Field("trophy", max_length=50)
    criteria: dict[str, Any] = Field(...)
    points_value: int = Field(0, ge=0)


class TeamAnalyticsResponse(BaseModel):
    """Response schema for team analytics (manager dashboard)."""

    team_velocity: int = 0
    trend: str = "+0%"
    total_points: int = 0
    active_users: int = 0
    top_performers: list[dict[str, Any]] = Field(default_factory=list)
    needs_attention: list[dict[str, Any]] = Field(default_factory=list)
    alerts: list[dict[str, Any]] = Field(default_factory=list)


class AlertResponse(BaseModel):
    """Response schema for predictive alerts."""

    type: str  # "burnout_risk", "disengagement", "bottleneck"
    employee_name: str
    employee_id: UUID
    severity: str  # "low", "medium", "high"
    recommendation: str
    data: dict[str, Any] = Field(default_factory=dict)
