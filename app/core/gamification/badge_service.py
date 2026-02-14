"""Badge service for gamification system."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.gamification import Badge, GamificationEvent, UserBadge

logger = get_logger(__name__)


class BadgeService:
    """Service for managing badges and awarding them to users."""

    def __init__(self, db: Session, tenant_id: UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def check_and_award_badges(
        self,
        user_id: UUID,
        event_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[UserBadge]:
        """Check all active badges and award any that the user qualifies for.

        Args:
            user_id: User to check badges for
            event_type: Type of event that triggered the check
            metadata: Additional context for criteria evaluation

        Returns:
            List of newly awarded UserBadge records
        """
        active_badges = (
            self.db.query(Badge)
            .filter(
                Badge.tenant_id == self.tenant_id,
                Badge.is_active.is_(True),
            )
            .all()
        )

        awarded: list[UserBadge] = []
        for badge in active_badges:
            if self._user_has_badge(user_id, badge.id):
                continue
            if self._evaluate_criteria(user_id, badge, event_type, metadata):
                user_badge = self._award_badge(user_id, badge)
                awarded.append(user_badge)
                logger.info(f"Badge '{badge.name}' awarded to user {user_id}")

        if awarded:
            self.db.commit()

        return awarded

    def get_user_badges(self, user_id: UUID) -> list[UserBadge]:
        """Get all badges earned by a user."""
        return (
            self.db.query(UserBadge)
            .filter(
                UserBadge.tenant_id == self.tenant_id,
                UserBadge.user_id == user_id,
            )
            .order_by(UserBadge.earned_at.desc())
            .all()
        )

    def create_badge(self, badge_data: dict[str, Any]) -> Badge:
        """Create a new badge definition (admin only).

        Args:
            badge_data: Badge fields (name, description, icon, criteria, points_value)

        Returns:
            Created Badge
        """
        badge = Badge(
            tenant_id=self.tenant_id,
            name=badge_data["name"],
            description=badge_data.get("description", ""),
            icon=badge_data.get("icon", "trophy"),
            criteria=badge_data["criteria"],
            points_value=badge_data.get("points_value", 0),
        )
        self.db.add(badge)
        self.db.commit()
        self.db.refresh(badge)
        return badge

    def list_badges(self, active_only: bool = True) -> list[Badge]:
        """List all badges for the tenant."""
        query = self.db.query(Badge).filter(Badge.tenant_id == self.tenant_id)
        if active_only:
            query = query.filter(Badge.is_active.is_(True))
        return query.order_by(Badge.name).all()

    def _user_has_badge(self, user_id: UUID, badge_id: UUID) -> bool:
        """Check if user already has a specific badge."""
        return (
            self.db.query(UserBadge)
            .filter(
                UserBadge.tenant_id == self.tenant_id,
                UserBadge.user_id == user_id,
                UserBadge.badge_id == badge_id,
            )
            .first()
            is not None
        )

    def _evaluate_criteria(
        self,
        user_id: UUID,
        badge: Badge,
        event_type: str,
        metadata: dict[str, Any] | None,
    ) -> bool:
        """Evaluate whether a user meets the criteria for a badge.

        Criteria format:
        {
            "event_type": "task_completed",
            "count": 10,           # minimum event count
            "min_level": 5,        # optional minimum level
            "min_streak": 7,       # optional minimum streak
        }
        """
        criteria = badge.criteria or {}

        # Check event type match
        required_event = criteria.get("event_type")
        if required_event and required_event != event_type:
            return False

        # Check event count
        required_count = criteria.get("count")
        if required_count:
            actual_count = (
                self.db.query(GamificationEvent)
                .filter(
                    GamificationEvent.tenant_id == self.tenant_id,
                    GamificationEvent.user_id == user_id,
                    GamificationEvent.event_type == (required_event or event_type),
                )
                .count()
            )
            if actual_count < required_count:
                return False

        return True

    def _award_badge(self, user_id: UUID, badge: Badge) -> UserBadge:
        """Award a badge to a user."""
        user_badge = UserBadge(
            tenant_id=self.tenant_id,
            user_id=user_id,
            badge_id=badge.id,
        )
        self.db.add(user_badge)
        self.db.flush()
        return user_badge
