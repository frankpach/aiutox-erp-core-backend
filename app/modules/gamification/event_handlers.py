"""Event handlers for gamification system.

Listens to PubSub events (task.completed, task.created, calendar.event_attended)
and awards points/badges accordingly.
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.gamification.badge_service import BadgeService
from app.core.gamification.leaderboard_service import LeaderboardService
from app.core.gamification.points_service import PointsService
from app.models.gamification import GamificationEvent

logger = logging.getLogger(__name__)

# Default points configuration
DEFAULT_POINTS_CONFIG: dict[str, dict[str, int]] = {
    "tasks": {
        "task.completed": 10,
        "task.created": 5,
    },
    "calendar": {
        "calendar.event_attended": 5,
    },
}

# Priority bonus points
PRIORITY_BONUS: dict[str, int] = {
    "urgent": 20,
    "high": 10,
    "medium": 0,
    "low": 0,
}

ON_TIME_BONUS = 15
STREAK_BONUS_THRESHOLD = 7
STREAK_BONUS_POINTS = 10


class GamificationEventHandler:
    """Handles PubSub events and awards gamification points/badges."""

    def __init__(
        self,
        db: Session,
        tenant_id: UUID,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.config = config or DEFAULT_POINTS_CONFIG
        self.points_service = PointsService(db, tenant_id)
        self.badge_service = BadgeService(db, tenant_id)
        self.leaderboard_service = LeaderboardService(db, tenant_id)

    def handle_task_completed(
        self,
        user_id: UUID,
        task_id: UUID,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Handle task.completed event.

        Awards base points + priority bonus + on-time bonus + streak bonus.
        Checks and awards badges. Updates leaderboard.

        Args:
            user_id: User who completed the task
            task_id: ID of the completed task
            metadata: Task metadata (priority, completed_on_time, etc.)
        """
        metadata = metadata or {}
        event_type = "task.completed"

        try:
            # Check idempotency
            if self._event_already_processed(user_id, event_type, task_id):
                logger.debug(f"Event {event_type} for task {task_id} already processed")
                return

            points = self._calculate_points(event_type, "tasks", metadata)

            self.points_service.add_points(
                user_id=user_id,
                points=points,
                event_type=event_type,
                source_module="tasks",
                source_id=task_id,
                metadata=metadata,
            )

            self.badge_service.check_and_award_badges(
                user_id=user_id,
                event_type=event_type,
                metadata=metadata,
            )

            self.leaderboard_service.update_user_score(user_id, "all_time")

            logger.info(
                f"task.completed: user={user_id}, task={task_id}, " f"points={points}"
            )
        except Exception as e:
            logger.error(f"Error handling task.completed: {e}", exc_info=True)

    def handle_task_created(
        self,
        user_id: UUID,
        task_id: UUID,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Handle task.created event.

        Awards base points for creating a task.

        Args:
            user_id: User who created the task
            task_id: ID of the created task
            metadata: Task metadata
        """
        metadata = metadata or {}
        event_type = "task.created"

        try:
            if self._event_already_processed(user_id, event_type, task_id):
                logger.debug(f"Event {event_type} for task {task_id} already processed")
                return

            points = self._calculate_points(event_type, "tasks", metadata)

            self.points_service.add_points(
                user_id=user_id,
                points=points,
                event_type=event_type,
                source_module="tasks",
                source_id=task_id,
                metadata=metadata,
            )

            logger.info(
                f"task.created: user={user_id}, task={task_id}, points={points}"
            )
        except Exception as e:
            logger.error(f"Error handling task.created: {e}", exc_info=True)

    def handle_event_attended(
        self,
        user_id: UUID,
        event_id: UUID,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Handle calendar.event_attended event.

        Awards base points for attending a calendar event.

        Args:
            user_id: User who attended the event
            event_id: ID of the calendar event
            metadata: Event metadata
        """
        metadata = metadata or {}
        event_type = "calendar.event_attended"

        try:
            if self._event_already_processed(user_id, event_type, event_id):
                logger.debug(
                    f"Event {event_type} for calendar event {event_id} already processed"
                )
                return

            points = self._calculate_points(event_type, "calendar", metadata)

            self.points_service.add_points(
                user_id=user_id,
                points=points,
                event_type=event_type,
                source_module="calendar",
                source_id=event_id,
                metadata=metadata,
            )

            self.badge_service.check_and_award_badges(
                user_id=user_id,
                event_type=event_type,
                metadata=metadata,
            )

            self.leaderboard_service.update_user_score(user_id, "all_time")

            logger.info(
                f"calendar.event_attended: user={user_id}, event={event_id}, "
                f"points={points}"
            )
        except Exception as e:
            logger.error(f"Error handling calendar.event_attended: {e}", exc_info=True)

    def _calculate_points(
        self,
        event_type: str,
        source_module: str,
        metadata: dict[str, Any],
    ) -> int:
        """Calculate total points for an event including bonuses.

        Args:
            event_type: Type of event
            source_module: Module that generated the event
            metadata: Event metadata for bonus calculation

        Returns:
            Total points to award
        """
        # Base points from config
        module_config = self.config.get(source_module, {})
        base_points = module_config.get(event_type, 10)

        # Priority bonus (only for task events)
        priority = metadata.get("priority", "medium")
        base_points += PRIORITY_BONUS.get(priority, 0)

        # On-time completion bonus
        if metadata.get("completed_on_time"):
            base_points += ON_TIME_BONUS

        # Streak bonus
        user_points = self.points_service.get_user_points(
            metadata.get("user_id", UUID(int=0))
        )
        if user_points and user_points.current_streak >= STREAK_BONUS_THRESHOLD:
            base_points += STREAK_BONUS_POINTS

        return base_points

    def _event_already_processed(
        self,
        user_id: UUID,
        event_type: str,
        source_id: UUID,
    ) -> bool:
        """Check if an event has already been processed (idempotency).

        Args:
            user_id: User ID
            event_type: Event type
            source_id: Source entity ID

        Returns:
            True if event was already processed
        """
        existing = (
            self.db.query(GamificationEvent)
            .filter(
                GamificationEvent.tenant_id == self.tenant_id,
                GamificationEvent.user_id == user_id,
                GamificationEvent.event_type == event_type,
                GamificationEvent.source_id == source_id,
            )
            .first()
        )
        return existing is not None
