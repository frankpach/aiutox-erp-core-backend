"""Calendar service for calendar and event management."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.core.notifications.service import NotificationService
from app.core.pubsub import EventPublisher, get_event_publisher
from app.core.pubsub.event_helpers import safe_publish_event
from app.core.pubsub.models import EventMetadata
from app.models.calendar import (
    Calendar,
    CalendarEvent,
    EventAttendee,
    EventReminder,
    EventStatus,
    ReminderType,
)
from app.repositories.calendar_repository import CalendarRepository

MIN_EVENT_DURATION = timedelta(minutes=15)

logger = logging.getLogger(__name__)


class CalendarService:
    """Service for calendar management."""

    def __init__(
        self,
        db: Session,
        event_publisher: EventPublisher | None = None,
        notification_service: NotificationService | None = None,
    ):
        """Initialize calendar service.

        Args:
            db: Database session
            event_publisher: EventPublisher instance (created if not provided)
            notification_service: NotificationService instance (created if not provided)
        """
        self.db = db
        self.repository = CalendarRepository(db)
        self.event_publisher = event_publisher or get_event_publisher()
        self.notification_service = notification_service or NotificationService(db)

    def create_calendar(
        self,
        calendar_data: dict,
        tenant_id: UUID,
        owner_id: UUID,
    ) -> Calendar:
        """Create a new calendar.

        Args:
            calendar_data: Calendar data
            tenant_id: Tenant ID
            owner_id: Owner user ID

        Returns:
            Created Calendar object
        """
        calendar_data["tenant_id"] = tenant_id
        calendar_data["owner_id"] = owner_id

        calendar = self.repository.create_calendar(calendar_data)

        # Publish event
        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="calendar.created",
            entity_type="calendar",
            entity_id=calendar.id,
            tenant_id=tenant_id,
            user_id=owner_id,
            metadata=EventMetadata(
                source="calendar_service",
                version="1.0",
                additional_data={"calendar_name": calendar.name},
            ),
        )

        return calendar

    def get_calendar(self, calendar_id: UUID, tenant_id: UUID) -> Calendar | None:
        """Get calendar by ID."""
        return self.repository.get_calendar_by_id(calendar_id, tenant_id)

    def get_user_calendars(
        self, user_id: UUID, tenant_id: UUID, calendar_type: str | None = None
    ) -> list[Calendar]:
        """Get calendars for a user."""
        return self.repository.get_calendars_by_owner(user_id, tenant_id, calendar_type)

    def update_calendar(
        self, calendar_id: UUID, tenant_id: UUID, calendar_data: dict
    ) -> Calendar | None:
        """Update calendar."""
        calendar = self.repository.get_calendar_by_id(calendar_id, tenant_id)
        if not calendar:
            return None

        return self.repository.update_calendar(calendar, calendar_data)

    def delete_calendar(self, calendar_id: UUID, tenant_id: UUID) -> bool:
        """Delete calendar."""
        calendar = self.repository.get_calendar_by_id(calendar_id, tenant_id)
        if not calendar:
            return False

        self.repository.delete_calendar(calendar)

        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="calendar.deleted",
            entity_type="calendar",
            entity_id=calendar.id,
            tenant_id=tenant_id,
            user_id=calendar.owner_id,
            metadata=EventMetadata(
                source="calendar_service",
                version="1.0",
                additional_data={"calendar_name": calendar.name},
            ),
        )

        return True

    def create_event(
        self,
        event_data: dict,
        tenant_id: UUID,
        organizer_id: UUID,
    ) -> CalendarEvent:
        """Create a new calendar event.

        Args:
            event_data: Event data
            tenant_id: Tenant ID
            organizer_id: Organizer user ID

        Returns:
            Created CalendarEvent object
        """
        event_data["tenant_id"] = tenant_id
        event_data["organizer_id"] = organizer_id
        event_data["status"] = event_data.get("status", EventStatus.SCHEDULED)

        event = self.repository.create_event(event_data)

        # Create reminders if specified
        if "reminders" in event_data:
            for reminder_data in event_data["reminders"]:
                reminder_data["event_id"] = event.id
                reminder_data["tenant_id"] = tenant_id
                self.repository.create_reminder(reminder_data)

        # Create attendees if specified
        if "attendees" in event_data:
            for attendee_data in event_data["attendees"]:
                attendee_data["event_id"] = event.id
                attendee_data["tenant_id"] = tenant_id
                self.repository.create_attendee(attendee_data)

        # Publish event
        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="calendar.event_created",
            entity_type="calendar_event",
            entity_id=event.id,
            tenant_id=tenant_id,
            user_id=organizer_id,
            metadata=EventMetadata(
                source="calendar_service",
                version="1.0",
                additional_data={
                    "event_title": event.title,
                    "calendar_id": str(event.calendar_id),
                    "start_time": event.start_time.isoformat(),
                },
            ),
        )

        return event

    def get_event(self, event_id: UUID, tenant_id: UUID) -> CalendarEvent | None:
        """Get event by ID."""
        return self.repository.get_event_by_id(event_id, tenant_id)

    def get_events_by_calendar(
        self,
        calendar_id: UUID,
        tenant_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CalendarEvent]:
        """Get events by calendar."""
        return self.repository.get_events_by_calendar(
            calendar_id, tenant_id, start_date, end_date, status, skip, limit
        )

    def get_user_events(
        self,
        user_id: UUID,
        tenant_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CalendarEvent]:
        """Get events for a user (as organizer or attendee)."""
        return self.repository.get_events_by_user(
            user_id, tenant_id, start_date, end_date, skip, limit
        )

    def count_events_by_calendar(
        self,
        calendar_id: UUID,
        tenant_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        status: str | None = None,
    ) -> int:
        """Count events by calendar with optional filters."""
        return self.repository.count_events_by_calendar(
            calendar_id, tenant_id, start_date, end_date, status
        )

    def count_user_events(
        self,
        user_id: UUID,
        tenant_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Count events for a user (as organizer or attendee)."""
        return self.repository.count_events_by_user(
            user_id, tenant_id, start_date, end_date
        )

    def update_event(
        self, event_id: UUID, tenant_id: UUID, event_data: dict
    ) -> CalendarEvent | None:
        """Update event.

        Raises:
            APIException: If resulting end_time <= start_time
        """
        event = self.repository.get_event_by_id(event_id, tenant_id)
        if not event:
            return None

        # Validate time range if start_time or end_time is being updated
        new_start = event_data.get("start_time", event.start_time)
        new_end = event_data.get("end_time", event.end_time)
        if new_end <= new_start:
            raise APIException(
                status_code=400,
                code="INVALID_EVENT_DURATION",
                message="end_time must be after start_time",
            )

        updated_event = self.repository.update_event(event, event_data)

        # Publish event
        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="calendar.event_updated",
            entity_type="calendar_event",
            entity_id=updated_event.id,
            tenant_id=tenant_id,
            user_id=updated_event.organizer_id,
            metadata=EventMetadata(
                source="calendar_service",
                version="1.0",
                additional_data={"event_title": updated_event.title},
            ),
        )

        return updated_event

    def move_event(
        self,
        event_id: UUID,
        tenant_id: UUID,
        new_start_time: datetime,
        preserve_duration: bool = True,
        scope: str = "single",
    ) -> CalendarEvent | None:
        """Move an event to a new start time.

        Args:
            event_id: Event ID
            tenant_id: Tenant ID
            new_start_time: New start time
            preserve_duration: Whether to preserve event duration
            scope: 'single' or 'series' (for recurring events)

        Returns:
            Updated CalendarEvent or None if not found
        """
        event = self.repository.get_event_by_id(event_id, tenant_id)
        if not event:
            return None

        # Calculate new end time
        if preserve_duration:
            duration = event.end_time - event.start_time
            new_end_time = new_start_time + duration
        else:
            new_end_time = new_start_time

        # Update event
        event_data = {
            "start_time": new_start_time,
            "end_time": new_end_time,
        }

        updated_event = self.update_event(event_id, tenant_id, event_data)

        # If event has source (e.g., task), sync back
        if updated_event and updated_event.source_type == "task":
            self._sync_event_to_source(updated_event)

        return updated_event

    def resize_event(
        self,
        event_id: UUID,
        tenant_id: UUID,
        new_end_time: datetime,
        scope: str = "single",
    ) -> CalendarEvent | None:
        """Resize an event by changing its end time.

        Args:
            event_id: Event ID
            tenant_id: Tenant ID
            new_end_time: New end time
            scope: 'single' or 'series' (for recurring events)

        Returns:
            Updated CalendarEvent or None if not found

        Raises:
            APIException: If new_end_time <= start_time or duration < 15 min
        """
        event = self.repository.get_event_by_id(event_id, tenant_id)
        if not event:
            return None

        # Validate end_time > start_time
        if new_end_time <= event.start_time:
            raise APIException(
                status_code=400,
                code="INVALID_EVENT_DURATION",
                message="end_time must be after start_time",
            )

        # Validate minimum duration (15 minutes)
        if (new_end_time - event.start_time) < MIN_EVENT_DURATION:
            raise APIException(
                status_code=400,
                code="INVALID_EVENT_DURATION",
                message="Minimum event duration is 15 minutes",
            )

        # Update event
        event_data = {
            "end_time": new_end_time,
        }

        updated_event = self.update_event(event_id, tenant_id, event_data)

        # If event has source (e.g., task), sync back
        if updated_event and updated_event.source_type == "task":
            self._sync_event_to_source(updated_event)

        return updated_event

    def _sync_event_to_source(self, event: CalendarEvent) -> None:
        """Sync event changes back to source entity.

        Args:
            event: CalendarEvent instance
        """
        if event.source_type == "task" and event.source_id:
            from app.core.calendar.sync_service import CalendarSyncService

            sync_service = CalendarSyncService(self.db)
            sync_service.sync_event_to_task(event)

    def cancel_event(self, event_id: UUID, tenant_id: UUID) -> CalendarEvent | None:
        """Cancel an event."""
        event = self.repository.get_event_by_id(event_id, tenant_id)
        if not event:
            return None

        updated_event = self.repository.update_event(
            event, {"status": EventStatus.CANCELLED}
        )

        # Publish event
        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="calendar.event_cancelled",
            entity_type="calendar_event",
            entity_id=updated_event.id,
            tenant_id=tenant_id,
            user_id=updated_event.organizer_id,
            metadata=EventMetadata(
                source="calendar_service",
                version="1.0",
                additional_data={"event_title": updated_event.title},
            ),
        )

        return updated_event

    def delete_event(self, event_id: UUID, tenant_id: UUID) -> bool:
        """Delete event."""
        event = self.repository.get_event_by_id(event_id, tenant_id)
        if not event:
            return False

        self.repository.delete_event(event)

        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="calendar.event_deleted",
            entity_type="calendar_event",
            entity_id=event_id,
            tenant_id=tenant_id,
            user_id=event.organizer_id,
            metadata=EventMetadata(
                source="calendar_service",
                version="1.0",
                additional_data={"event_title": event.title},
            ),
        )

        return True

    def add_attendee(
        self,
        event_id: UUID,
        tenant_id: UUID,
        attendee_data: dict,
    ) -> EventAttendee:
        """Add attendee to event."""
        attendee_data["event_id"] = event_id
        attendee_data["tenant_id"] = tenant_id
        return self.repository.create_attendee(attendee_data)

    def update_attendee_response(
        self,
        event_id: UUID,
        user_id: UUID,
        tenant_id: UUID,
        status: str,
        comment: str | None = None,
    ) -> EventAttendee | None:
        """Update attendee response."""
        attendee = self.repository.get_attendee_by_event_and_user(
            event_id, user_id, tenant_id
        )
        if not attendee:
            return None

        from datetime import UTC, datetime

        update_data = {
            "status": status,
            "response_at": datetime.now(UTC),
        }
        if comment:
            update_data["comment"] = comment

        return self.repository.update_attendee(attendee, update_data)

    def add_reminder(
        self,
        event_id: UUID,
        tenant_id: UUID,
        reminder_data: dict,
    ) -> EventReminder:
        """Add reminder to event.

        Validates:
        - minutes_before between 5 and 10080 (1 week)
        - reminder_type is one of: email, in_app, push
        - Maximum 5 reminders per event
        """
        minutes_before = reminder_data.get("minutes_before", 0)
        if (
            not isinstance(minutes_before, int)
            or minutes_before < 5
            or minutes_before > 10080
        ):
            raise APIException(
                status_code=400,
                code="INVALID_REMINDER_MINUTES",
                message="minutes_before must be between 5 and 10080",
            )

        reminder_type = reminder_data.get("reminder_type", "")
        valid_types = {"email", "in_app", "push"}
        if reminder_type not in valid_types:
            raise APIException(
                status_code=400,
                code="INVALID_REMINDER_TYPE",
                message=f"reminder_type must be one of: {', '.join(sorted(valid_types))}",
            )

        current_count = self.count_event_reminders(event_id, tenant_id)
        if current_count >= 5:
            raise APIException(
                status_code=400,
                code="REMINDER_LIMIT_EXCEEDED",
                message="Maximum 5 reminders per event",
            )

        reminder_data["event_id"] = event_id
        reminder_data["tenant_id"] = tenant_id
        return self.repository.create_reminder(reminder_data)

    def get_event_reminders(
        self,
        event_id: UUID,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> list[EventReminder]:
        """Get reminders for an event."""
        return self.repository.get_event_reminders(
            event_id=event_id,
            tenant_id=tenant_id,
            skip=skip,
            limit=limit,
        )

    def count_event_reminders(
        self,
        event_id: UUID,
        tenant_id: UUID,
    ) -> int:
        """Count reminders for an event."""
        return self.repository.count_event_reminders(
            event_id=event_id,
            tenant_id=tenant_id,
        )

    def delete_reminder(
        self,
        reminder_id: UUID,
        tenant_id: UUID,
    ) -> bool:
        """Delete a reminder."""
        reminder = self.repository.get_reminder_by_id(reminder_id, tenant_id)
        if not reminder:
            return False

        return self.repository.delete_reminder(reminder)


class ReminderService:
    """Service for managing event reminders."""

    def __init__(
        self,
        db: Session,
        notification_service: NotificationService | None = None,
        event_publisher: EventPublisher | None = None,
    ):
        """Initialize reminder service.

        Args:
            db: Database session
            notification_service: NotificationService instance
            event_publisher: EventPublisher instance
        """
        self.db = db
        self.repository = CalendarRepository(db)
        self.notification_service = notification_service or NotificationService(db)
        self.event_publisher = event_publisher or get_event_publisher()

    def get_pending_reminders(
        self, tenant_id: UUID, before_time: datetime | None = None
    ) -> list[EventReminder]:
        """Get pending reminders that should be sent.

        Args:
            tenant_id: Tenant ID
            before_time: Time before which reminders should be sent (defaults to now)

        Returns:
            List of pending reminders
        """
        if before_time is None:
            before_time = datetime.now(UTC)

        return self.repository.get_pending_reminders(tenant_id, before_time)

    async def send_reminder(self, reminder: EventReminder) -> bool:
        """Send a reminder.

        Args:
            reminder: Reminder to send

        Returns:
            True if sent successfully, False otherwise
        """
        event = self.repository.get_event_by_id(reminder.event_id, reminder.tenant_id)
        if not event or event.status == EventStatus.CANCELLED:
            logger.warning(
                f"Event {reminder.event_id} not found or cancelled, skipping reminder"
            )
            return False

        # Calculate when reminder should be sent
        reminder_time = event.start_time - timedelta(minutes=reminder.minutes_before)
        now = datetime.now(UTC)

        # Only send if it's time (or past time)
        if reminder_time > now:
            logger.debug(f"Reminder {reminder.id} not yet due (due at {reminder_time})")
            return False

        # Send notification based on reminder type
        try:
            if reminder.reminder_type == ReminderType.EMAIL:
                # Send email notification
                await self.notification_service.send(
                    event_type="calendar.event_reminder",
                    recipient_id=event.organizer_id or reminder.tenant_id,  # Fallback
                    channels=["email"],
                    data={
                        "event_title": event.title,
                        "event_start": event.start_time.isoformat(),
                        "event_location": event.location,
                    },
                    tenant_id=reminder.tenant_id,
                )
            elif reminder.reminder_type == ReminderType.IN_APP:
                # Send in-app notification
                await self.notification_service.send(
                    event_type="calendar.event_reminder",
                    recipient_id=event.organizer_id or reminder.tenant_id,
                    channels=["in-app"],
                    data={
                        "event_title": event.title,
                        "event_start": event.start_time.isoformat(),
                    },
                    tenant_id=reminder.tenant_id,
                )
            elif reminder.reminder_type == ReminderType.PUSH:
                # Send push notification (future implementation)
                logger.info(
                    f"Push notifications not yet implemented for reminder {reminder.id}"
                )

            # Mark reminder as sent
            self.repository.update_reminder(
                reminder,
                {
                    "is_sent": True,
                    "sent_at": datetime.now(UTC),
                },
            )

            # Publish event
            safe_publish_event(
                event_publisher=self.event_publisher,
                event_type="calendar.event_reminder_sent",
                entity_type="calendar_event",
                entity_id=event.id,
                tenant_id=reminder.tenant_id,
                user_id=event.organizer_id,
                metadata=EventMetadata(
                    source="reminder_service",
                    version="1.0",
                    additional_data={
                        "event_title": event.title,
                        "reminder_type": reminder.reminder_type,
                        "minutes_before": reminder.minutes_before,
                    },
                ),
            )

            return True

        except Exception as e:
            logger.error(f"Failed to send reminder {reminder.id}: {e}", exc_info=True)
            return False

    async def process_pending_reminders(
        self, tenant_id: UUID | None = None
    ) -> list[dict[str, Any]]:
        """Process all pending reminders.

        Args:
            tenant_id: Tenant ID (optional, processes all tenants if None)

        Returns:
            List of results for each reminder processed
        """
        # For now, we'll process reminders for a specific tenant
        # In production, this would be a background task that processes all tenants
        if tenant_id is None:
            logger.warning("tenant_id is required for processing reminders")
            return []

        pending_reminders = self.get_pending_reminders(tenant_id)
        results = []

        for reminder in pending_reminders:
            success = await self.send_reminder(reminder)
            results.append(
                {
                    "reminder_id": str(reminder.id),
                    "event_id": str(reminder.event_id),
                    "success": success,
                }
            )

        return results
