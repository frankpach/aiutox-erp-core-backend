"""Gamification repository for data access operations."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.gamification import (
    Badge,
    GamificationEvent,
    LeaderboardEntry,
    UserBadge,
    UserPoints,
)


class GamificationRepository:
    """Repository for gamification data access."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # --- UserPoints ---

    def get_user_points(self, user_id: UUID, tenant_id: UUID) -> UserPoints | None:
        """Get user points record."""
        return (
            self.db.query(UserPoints)
            .filter(
                UserPoints.tenant_id == tenant_id,
                UserPoints.user_id == user_id,
            )
            .first()
        )

    def get_or_create_user_points(self, user_id: UUID, tenant_id: UUID) -> UserPoints:
        """Get existing user points or create a new record."""
        user_points = self.get_user_points(user_id, tenant_id)
        if not user_points:
            user_points = UserPoints(
                tenant_id=tenant_id,
                user_id=user_id,
                total_points=0,
                level=1,
                current_streak=0,
                longest_streak=0,
            )
            self.db.add(user_points)
            self.db.flush()
        return user_points

    def get_team_points(
        self, user_ids: list[UUID], tenant_id: UUID
    ) -> list[UserPoints]:
        """Get points for a list of users."""
        return (
            self.db.query(UserPoints)
            .filter(
                UserPoints.tenant_id == tenant_id,
                UserPoints.user_id.in_(user_ids),
            )
            .all()
        )

    # --- GamificationEvent ---

    def create_event(
        self,
        tenant_id: UUID,
        user_id: UUID,
        event_type: str,
        source_module: str,
        points_earned: int,
        source_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GamificationEvent:
        """Create a gamification event."""
        event = GamificationEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            source_module=source_module,
            source_id=source_id,
            points_earned=points_earned,
            metadata=metadata,
        )
        self.db.add(event)
        return event

    def get_user_events(
        self, user_id: UUID, tenant_id: UUID, limit: int = 50
    ) -> list[GamificationEvent]:
        """Get recent events for a user."""
        return (
            self.db.query(GamificationEvent)
            .filter(
                GamificationEvent.tenant_id == tenant_id,
                GamificationEvent.user_id == user_id,
            )
            .order_by(GamificationEvent.created_at.desc())
            .limit(limit)
            .all()
        )

    def count_events_by_type(
        self, user_id: UUID, tenant_id: UUID, event_type: str
    ) -> int:
        """Count events of a specific type for a user."""
        return (
            self.db.query(GamificationEvent)
            .filter(
                GamificationEvent.tenant_id == tenant_id,
                GamificationEvent.user_id == user_id,
                GamificationEvent.event_type == event_type,
            )
            .count()
        )

    def event_exists(
        self, tenant_id: UUID, user_id: UUID, event_type: str, source_id: UUID
    ) -> bool:
        """Check if an event already exists (idempotency)."""
        return (
            self.db.query(GamificationEvent)
            .filter(
                GamificationEvent.tenant_id == tenant_id,
                GamificationEvent.user_id == user_id,
                GamificationEvent.event_type == event_type,
                GamificationEvent.source_id == source_id,
            )
            .first()
            is not None
        )

    # --- Badge ---

    def list_badges(
        self, tenant_id: UUID, active_only: bool = True
    ) -> list[Badge]:
        """List badges for a tenant."""
        query = self.db.query(Badge).filter(Badge.tenant_id == tenant_id)
        if active_only:
            query = query.filter(Badge.is_active.is_(True))
        return query.order_by(Badge.name).all()

    def create_badge(self, badge_data: dict[str, Any]) -> Badge:
        """Create a new badge."""
        badge = Badge(**badge_data)
        self.db.add(badge)
        self.db.commit()
        self.db.refresh(badge)
        return badge

    def get_user_badges(
        self, user_id: UUID, tenant_id: UUID
    ) -> list[UserBadge]:
        """Get badges earned by a user."""
        return (
            self.db.query(UserBadge)
            .filter(
                UserBadge.tenant_id == tenant_id,
                UserBadge.user_id == user_id,
            )
            .order_by(UserBadge.earned_at.desc())
            .all()
        )

    def user_has_badge(
        self, user_id: UUID, badge_id: UUID, tenant_id: UUID
    ) -> bool:
        """Check if user already has a specific badge."""
        return (
            self.db.query(UserBadge)
            .filter(
                UserBadge.tenant_id == tenant_id,
                UserBadge.user_id == user_id,
                UserBadge.badge_id == badge_id,
            )
            .first()
            is not None
        )

    def award_badge(
        self, user_id: UUID, badge_id: UUID, tenant_id: UUID
    ) -> UserBadge:
        """Award a badge to a user."""
        user_badge = UserBadge(
            tenant_id=tenant_id,
            user_id=user_id,
            badge_id=badge_id,
        )
        self.db.add(user_badge)
        self.db.flush()
        return user_badge

    # --- Leaderboard ---

    def get_leaderboard(
        self, tenant_id: UUID, period: str = "all_time", limit: int = 10
    ) -> list[LeaderboardEntry]:
        """Get leaderboard entries for a period."""
        return (
            self.db.query(LeaderboardEntry)
            .filter(
                LeaderboardEntry.tenant_id == tenant_id,
                LeaderboardEntry.period == period,
            )
            .order_by(LeaderboardEntry.points.desc())
            .limit(limit)
            .all()
        )

    def get_user_rank(
        self, user_id: UUID, tenant_id: UUID, period: str = "all_time"
    ) -> LeaderboardEntry | None:
        """Get a user's leaderboard entry."""
        return (
            self.db.query(LeaderboardEntry)
            .filter(
                LeaderboardEntry.tenant_id == tenant_id,
                LeaderboardEntry.user_id == user_id,
                LeaderboardEntry.period == period,
            )
            .first()
        )
