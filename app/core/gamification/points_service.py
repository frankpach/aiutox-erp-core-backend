"""Points service for gamification system."""

import math
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.gamification import GamificationEvent, UserPoints

logger = get_logger(__name__)


class PointsService:
    """Service for managing user points, levels, and streaks."""

    def __init__(self, db: Session, tenant_id: UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def add_points(
        self,
        user_id: UUID,
        points: int,
        event_type: str,
        source_module: str,
        source_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UserPoints:
        """Add points to a user and record the event.

        Args:
            user_id: User receiving points
            points: Number of points to add
            event_type: Type of event (e.g., "task_completed")
            source_module: Module that generated the event
            source_id: ID of the source entity
            metadata: Additional event metadata

        Returns:
            Updated UserPoints record
        """
        # Record the event
        event = GamificationEvent(
            tenant_id=self.tenant_id,
            user_id=user_id,
            event_type=event_type,
            source_module=source_module,
            source_id=source_id,
            points_earned=points,
            event_metadata=metadata,
        )
        self.db.add(event)

        # Get or create user points
        user_points = self._get_or_create_user_points(user_id)

        # Update points and level
        user_points.total_points += points
        new_level = self.calculate_level(user_points.total_points)
        level_up = new_level > user_points.level
        user_points.level = new_level

        # Update streak
        self._update_streak(user_points)

        self.db.commit()
        self.db.refresh(user_points)

        if level_up:
            logger.info(
                f"User {user_id} leveled up to {new_level} "
                f"(total: {user_points.total_points} points)"
            )

        return user_points

    def get_user_points(self, user_id: UUID) -> UserPoints | None:
        """Get user points record."""
        return (
            self.db.query(UserPoints)
            .filter(
                UserPoints.tenant_id == self.tenant_id,
                UserPoints.user_id == user_id,
            )
            .first()
        )

    @staticmethod
    def calculate_level(total_points: int) -> int:
        """Calculate level from total points.

        Formula: level = floor(sqrt(points / 100)) + 1
        Level 1: 0-99 pts, Level 2: 100-399 pts, Level 3: 400-899 pts, etc.
        """
        if total_points <= 0:
            return 1
        return int(math.sqrt(total_points / 100)) + 1

    @staticmethod
    def points_for_level(level: int) -> int:
        """Calculate minimum points needed for a given level."""
        if level <= 1:
            return 0
        return (level - 1) ** 2 * 100

    def get_user_events(
        self,
        user_id: UUID,
        limit: int = 50,
    ) -> list[GamificationEvent]:
        """Get recent gamification events for a user."""
        return (
            self.db.query(GamificationEvent)
            .filter(
                GamificationEvent.tenant_id == self.tenant_id,
                GamificationEvent.user_id == user_id,
            )
            .order_by(GamificationEvent.created_at.desc())
            .limit(limit)
            .all()
        )

    def _get_or_create_user_points(self, user_id: UUID) -> UserPoints:
        """Get existing user points or create a new record."""
        user_points = self.get_user_points(user_id)
        if not user_points:
            user_points = UserPoints(
                tenant_id=self.tenant_id,
                user_id=user_id,
                total_points=0,
                level=1,
                current_streak=0,
                longest_streak=0,
            )
            self.db.add(user_points)
            self.db.flush()
        return user_points

    def _update_streak(self, user_points: UserPoints) -> None:
        """Update daily activity streak."""
        today = date.today()

        if user_points.last_activity_date is None:
            user_points.current_streak = 1
        elif user_points.last_activity_date == today:
            pass  # Already counted today
        elif (today - user_points.last_activity_date).days == 1:
            user_points.current_streak += 1
        else:
            user_points.current_streak = 1  # Streak broken

        user_points.last_activity_date = today
        if user_points.current_streak > user_points.longest_streak:
            user_points.longest_streak = user_points.current_streak
