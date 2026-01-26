"""Task scheduler for automatic reminders and notifications."""

from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.core.config_file import get_settings
from app.core.db.session import SessionLocal
from app.core.logging import get_logger
from app.core.pubsub import get_event_publisher
from app.core.pubsub.models import EventMetadata
from app.models.task import Task, TaskStatusEnum
from app.repositories.task_repository import TaskRepository

logger = get_logger(__name__)
settings = get_settings()


class TaskScheduler:
    """Scheduler for task reminders and automatic notifications."""

    def __init__(self):
        """Initialize task scheduler."""
        self.scheduler = AsyncIOScheduler()
        self._running = False
        logger.info("TaskScheduler initialized")

    async def start(self) -> None:
        """Start the task scheduler."""
        if self._running:
            logger.warning("TaskScheduler is already running")
            return

        try:
            # Schedule check for tasks due soon (every 15 minutes)
            self.scheduler.add_job(
                self.check_due_soon_tasks,
                trigger=IntervalTrigger(minutes=15),
                id="check_due_soon_tasks",
                name="Check tasks due soon",
                replace_existing=True,
            )

            # Schedule check for overdue tasks (every hour)
            self.scheduler.add_job(
                self.check_overdue_tasks,
                trigger=IntervalTrigger(hours=1),
                id="check_overdue_tasks",
                name="Check overdue tasks",
                replace_existing=True,
            )

            self.scheduler.start()
            self._running = True
            logger.info("TaskScheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start TaskScheduler: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Stop the task scheduler."""
        if not self._running:
            logger.warning("TaskScheduler is not running")
            return

        try:
            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("TaskScheduler stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping TaskScheduler: {e}", exc_info=True)

    async def check_due_soon_tasks(self) -> None:
        """Check for tasks due soon and publish events.

        Checks for tasks due in:
        - 24 hours
        - 1 hour
        - 15 minutes
        """
        db: Session = SessionLocal()
        try:
            repository = TaskRepository(db)
            event_publisher = get_event_publisher()
            now = datetime.now(UTC)

            # Define time windows for notifications
            time_windows = [
                (timedelta(hours=24), timedelta(hours=23, minutes=45), "24h"),
                (timedelta(hours=1), timedelta(minutes=45), "1h"),
                (timedelta(minutes=15), timedelta(minutes=0), "15min"),
            ]

            for max_delta, min_delta, window_name in time_windows:
                due_start = now + min_delta
                due_end = now + max_delta

                # Get tasks due in this window
                tasks = self._get_tasks_in_window(repository, due_start, due_end)

                for task in tasks:
                    # Check if notification was already sent for this window
                    if self._should_send_notification(task, window_name):
                        await self._publish_due_soon_event(
                            task, event_publisher, window_name
                        )
                        logger.info(
                            f"Published due_soon event for task {task.id} ({window_name})"
                        )

            logger.info(f"Checked {len(time_windows)} time windows for due soon tasks")
        except Exception as e:
            logger.error(f"Error checking due soon tasks: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            db.close()

    async def check_overdue_tasks(self) -> None:
        """Check for overdue tasks and publish events."""
        db: Session = SessionLocal()
        try:
            event_publisher = get_event_publisher()
            now = datetime.now(UTC)

            # Get overdue tasks (not completed and past due date)
            overdue_tasks = (
                db.query(Task)
                .filter(
                    Task.due_date < now,
                    Task.status.notin_([TaskStatusEnum.DONE, TaskStatusEnum.CANCELLED]),
                )
                .all()
            )

            for task in overdue_tasks:
                # Publish overdue event
                await self._publish_overdue_event(task, event_publisher)
                logger.info(f"Published overdue event for task {task.id}")

            logger.info(f"Checked {len(overdue_tasks)} overdue tasks")
        except Exception as e:
            logger.error(f"Error checking overdue tasks: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            db.close()

    def _get_tasks_in_window(
        self, repository: TaskRepository, start: datetime, end: datetime
    ) -> list[Task]:
        """Get tasks with due dates in the specified time window.

        Args:
            repository: Task repository
            start: Start of time window
            end: End of time window

        Returns:
            List of tasks due in the window
        """
        return (
            repository.db.query(Task)
            .filter(
                Task.due_date >= start,
                Task.due_date <= end,
                Task.status.notin_([TaskStatusEnum.DONE, TaskStatusEnum.CANCELLED]),
            )
            .all()
        )

    def _should_send_notification(self, task: Task, window_name: str) -> bool:
        """Check if notification should be sent for this task and window.

        Args:
            task: Task to check
            window_name: Time window name (24h, 1h, 15min)

        Returns:
            True if notification should be sent
        """
        # Check metadata for already sent notifications
        if not task.metadata:
            return True

        notifications_sent = task.metadata.get("notifications_sent", {})
        last_sent = notifications_sent.get(f"due_soon_{window_name}")

        if not last_sent:
            return True

        # Don't send duplicate notifications
        return False

    async def _publish_due_soon_event(
        self, task: Task, event_publisher, window_name: str
    ) -> None:
        """Publish task.due_soon event.

        Args:
            task: Task that is due soon
            event_publisher: Event publisher instance
            window_name: Time window name
        """
        from app.core.pubsub.event_helpers import safe_publish_event

        safe_publish_event(
            event_publisher=event_publisher,
            event_type="task.due_soon",
            entity_type="task",
            entity_id=task.id,
            tenant_id=task.tenant_id,
            user_id=task.assigned_to_id or task.created_by_id,
            metadata=EventMetadata(
                source="task_scheduler",
                version="1.0",
                additional_data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "window": window_name,
                    "assigned_to_id": str(task.assigned_to_id) if task.assigned_to_id else None,
                    "created_by_id": str(task.created_by_id),
                },
            ),
        )

        # Update task metadata to mark notification as sent
        if not task.metadata:
            task.metadata = {}
        if "notifications_sent" not in task.metadata:
            task.metadata["notifications_sent"] = {}

        task.metadata["notifications_sent"][f"due_soon_{window_name}"] = (
            datetime.now(UTC).isoformat()
        )
        task.metadata = dict(task.metadata)  # Force SQLAlchemy to detect change

    async def _publish_overdue_event(self, task: Task, event_publisher) -> None:
        """Publish task.overdue event.

        Args:
            task: Overdue task
            event_publisher: Event publisher instance
        """
        from app.core.pubsub.event_helpers import safe_publish_event

        days_overdue = (datetime.now(UTC) - task.due_date).days if task.due_date else 0

        safe_publish_event(
            event_publisher=event_publisher,
            event_type="task.overdue",
            entity_type="task",
            entity_id=task.id,
            tenant_id=task.tenant_id,
            user_id=task.assigned_to_id or task.created_by_id,
            metadata=EventMetadata(
                source="task_scheduler",
                version="1.0",
                additional_data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "days_overdue": days_overdue,
                    "assigned_to_id": str(task.assigned_to_id) if task.assigned_to_id else None,
                    "created_by_id": str(task.created_by_id),
                },
            ),
        )


# Global scheduler instance
_task_scheduler: TaskScheduler | None = None


async def get_task_scheduler() -> TaskScheduler:
    """Get or create the global TaskScheduler instance.

    Returns:
        TaskScheduler instance
    """
    global _task_scheduler

    if _task_scheduler is None:
        _task_scheduler = TaskScheduler()
        await _task_scheduler.start()

    return _task_scheduler


async def stop_task_scheduler() -> None:
    """Stop the global TaskScheduler instance."""
    global _task_scheduler

    if _task_scheduler is not None:
        await _task_scheduler.stop()
        _task_scheduler = None
