"""Time tracking service for task work sessions."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.task import Task
from app.models.time_entry import TimeEntry

logger = get_logger(__name__)


class TimeTrackingService:
    """Service for managing time entries on tasks."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def start_session(
        self,
        task_id: UUID,
        user_id: UUID,
        tenant_id: UUID,
        notes: str | None = None,
    ) -> TimeEntry:
        """Start a new time tracking session.

        Args:
            task_id: Task to track time for
            user_id: User starting the session
            tenant_id: Tenant ID
            notes: Optional notes

        Returns:
            Created TimeEntry

        Raises:
            ValueError: If user already has an active session on this task
        """
        # Check task exists
        task = (
            self.db.query(Task)
            .filter(Task.id == task_id, Task.tenant_id == tenant_id)
            .first()
        )
        if not task:
            raise ValueError("Task not found")

        # Check for existing active session
        active = (
            self.db.query(TimeEntry)
            .filter(
                TimeEntry.task_id == task_id,
                TimeEntry.user_id == user_id,
                TimeEntry.tenant_id == tenant_id,
                TimeEntry.end_time.is_(None),
            )
            .first()
        )
        if active:
            raise ValueError("Active session already exists for this task")

        entry = TimeEntry(
            task_id=task_id,
            user_id=user_id,
            tenant_id=tenant_id,
            start_time=datetime.now(UTC),
            notes=notes,
            entry_type="timer",
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        logger.info(f"Time session started: {entry.id} for task {task_id}")
        return entry

    def stop_session(
        self,
        entry_id: UUID,
        user_id: UUID,
        tenant_id: UUID,
    ) -> TimeEntry:
        """Stop an active time tracking session.

        Args:
            entry_id: TimeEntry ID to stop
            user_id: User stopping the session
            tenant_id: Tenant ID

        Returns:
            Updated TimeEntry with end_time and duration

        Raises:
            ValueError: If entry not found or already stopped
        """
        entry = (
            self.db.query(TimeEntry)
            .filter(
                TimeEntry.id == entry_id,
                TimeEntry.user_id == user_id,
                TimeEntry.tenant_id == tenant_id,
            )
            .first()
        )
        if not entry:
            raise ValueError("Time entry not found")
        if entry.end_time is not None:
            raise ValueError("Session already stopped")

        now = datetime.now(UTC)
        entry.end_time = now
        entry.duration_seconds = (now - entry.start_time).total_seconds()

        self.db.commit()
        self.db.refresh(entry)

        # Update task actual_hours
        self._update_task_actual_hours(entry.task_id, tenant_id)

        logger.info(
            f"Time session stopped: {entry.id}, duration: {entry.duration_seconds}s"
        )
        return entry

    def get_active_session(
        self,
        task_id: UUID,
        user_id: UUID,
        tenant_id: UUID,
    ) -> TimeEntry | None:
        """Get the active (running) session for a user on a task."""
        return (
            self.db.query(TimeEntry)
            .filter(
                TimeEntry.task_id == task_id,
                TimeEntry.user_id == user_id,
                TimeEntry.tenant_id == tenant_id,
                TimeEntry.end_time.is_(None),
            )
            .first()
        )

    def list_entries(
        self,
        task_id: UUID,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[TimeEntry]:
        """List time entries for a task."""
        return (
            self.db.query(TimeEntry)
            .filter(
                TimeEntry.task_id == task_id,
                TimeEntry.tenant_id == tenant_id,
            )
            .order_by(TimeEntry.start_time.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def delete_entry(
        self,
        entry_id: UUID,
        user_id: UUID,
        tenant_id: UUID,
    ) -> bool:
        """Delete a time entry (only own entries)."""
        entry = (
            self.db.query(TimeEntry)
            .filter(
                TimeEntry.id == entry_id,
                TimeEntry.user_id == user_id,
                TimeEntry.tenant_id == tenant_id,
            )
            .first()
        )
        if not entry:
            return False

        task_id = entry.task_id
        self.db.delete(entry)
        self.db.commit()

        # Recalculate actual hours
        self._update_task_actual_hours(task_id, tenant_id)
        return True

    def create_manual_entry(
        self,
        task_id: UUID,
        user_id: UUID,
        tenant_id: UUID,
        start_time: datetime,
        end_time: datetime,
        notes: str | None = None,
    ) -> TimeEntry:
        """Create a manual time entry (not from timer).

        Args:
            task_id: Task ID
            user_id: User ID
            tenant_id: Tenant ID
            start_time: Start time
            end_time: End time
            notes: Optional notes

        Returns:
            Created TimeEntry

        Raises:
            ValueError: If end_time <= start_time or task not found
        """
        if end_time <= start_time:
            raise ValueError("End time must be after start time")

        task = (
            self.db.query(Task)
            .filter(Task.id == task_id, Task.tenant_id == tenant_id)
            .first()
        )
        if not task:
            raise ValueError("Task not found")

        duration = (end_time - start_time).total_seconds()
        entry = TimeEntry(
            task_id=task_id,
            user_id=user_id,
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            notes=notes,
            entry_type="manual",
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        self._update_task_actual_hours(task_id, tenant_id)
        return entry

    def get_task_total_hours(self, task_id: UUID, tenant_id: UUID) -> float:
        """Calculate total tracked hours for a task."""
        entries = (
            self.db.query(TimeEntry)
            .filter(
                TimeEntry.task_id == task_id,
                TimeEntry.tenant_id == tenant_id,
                TimeEntry.duration_seconds.isnot(None),
            )
            .all()
        )
        total_seconds = sum(e.duration_seconds for e in entries if e.duration_seconds)
        return round(total_seconds / 3600, 2)

    def _update_task_actual_hours(self, task_id: UUID, tenant_id: UUID) -> None:
        """Recalculate and update task.actual_hours from time entries."""
        total_hours = self.get_task_total_hours(task_id, tenant_id)
        task = (
            self.db.query(Task)
            .filter(Task.id == task_id, Task.tenant_id == tenant_id)
            .first()
        )
        if task and hasattr(task, "task_metadata"):
            # Store in metadata since estimated_hours/actual_hours
            # columns may not exist yet (pending migration)
            metadata = task.task_metadata or {}
            metadata["actual_hours"] = total_hours
            task.task_metadata = metadata
            self.db.commit()
