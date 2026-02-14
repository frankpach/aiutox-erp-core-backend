"""Gamification models for AiutoX ERP."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class GamificationEvent(Base):
    """Events that generate points (task completed, event attended, etc.)."""

    __tablename__ = "gamification_events"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(50), nullable=False)  # "task_completed", "streak_bonus"
    source_module = Column(String(50), nullable=False)  # "tasks", "calendar"
    source_id = Column(PG_UUID(as_uuid=True), nullable=True)
    points_earned = Column(Integer, nullable=False, default=0)
    event_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_gam_events_user", "tenant_id", "user_id"),
        Index("idx_gam_events_type", "tenant_id", "event_type"),
    )

    def __repr__(self) -> str:
        return f"<GamificationEvent(id={self.id}, type={self.event_type}, points={self.points_earned})>"

class UserPoints(Base):
    """Accumulated points and level per user per tenant."""

    __tablename__ = "user_points"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    total_points = Column(Integer, nullable=False, default=0)
    level = Column(Integer, nullable=False, default=1)
    current_streak = Column(Integer, nullable=False, default=0)
    longest_streak = Column(Integer, nullable=False, default=0)
    last_activity_date = Column(Date, nullable=True)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_user_points_unique", "tenant_id", "user_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<UserPoints(user={self.user_id}, points={self.total_points}, level={self.level})>"


class Badge(Base):
    """Badge definitions per tenant."""

    __tablename__ = "badges"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=False, default="trophy")
    criteria = Column(JSON, nullable=False)  # {"event_type": "task_completed", "count": 10}
    points_value = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user_badges = relationship("UserBadge", back_populates="badge")

    __table_args__ = (
        Index("idx_badges_tenant", "tenant_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Badge(id={self.id}, name={self.name})>"


class UserBadge(Base):
    """Badges earned by users."""

    __tablename__ = "user_badges"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    badge_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("badges.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_event_id = Column(PG_UUID(as_uuid=True), nullable=True)
    earned_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    badge = relationship("Badge", back_populates="user_badges")

    __table_args__ = (
        Index("idx_user_badges_user", "tenant_id", "user_id"),
        Index("idx_user_badges_unique", "tenant_id", "user_id", "badge_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<UserBadge(user={self.user_id}, badge={self.badge_id})>"


class LeaderboardEntry(Base):
    """Cached leaderboard rankings."""

    __tablename__ = "leaderboard_entries"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    period = Column(String(20), nullable=False)  # "daily", "weekly", "monthly", "all_time"
    points = Column(Integer, nullable=False, default=0)
    rank = Column(Integer, nullable=True)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_leaderboard_period", "tenant_id", "period", "points"),
        Index("idx_leaderboard_unique", "tenant_id", "user_id", "period", unique=True),
    )

    def __repr__(self) -> str:
        return f"<LeaderboardEntry(user={self.user_id}, period={self.period}, points={self.points})>"
