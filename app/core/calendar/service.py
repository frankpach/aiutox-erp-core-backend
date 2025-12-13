"""Calendar service for calendar and event management."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.notifications.service import NotificationService
from app.core.pubsub import EventPublisher, get_event_publisher
from app.core.pubsub.models import EventMetadata
from app.models.calendar import (
    Calendar,
    CalendarEvent,
    EventAttendee,
    EventReminder,
    EventStatus,
    RecurrenceType,
    ReminderType,
)
from app.repositories.calendar_repository import CalendarRepository

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
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self.event_publisher.publish(
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
                )
            else:
                loop.run_until_complete(
                    self.event_publisher.publish(
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
                )
        except Exception as e:
            logger.error(f"Failed to publish calendar.created event: {e}")

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
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self.event_publisher.publish(
                        event_type="calendar.event.created",
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
                )
            else:
                loop.run_until_complete(
                    self.event_publisher.publish(
                        event_type="calendar.event.created",
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
                )
        except Exception as e:
            logger.error(f"Failed to publish calendar.event.created event: {e}")

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

    def update_event(
        self, event_id: UUID, tenant_id: UUID, event_data: dict
    ) -> CalendarEvent | None:
        """Update event."""
        event = self.repository.get_event_by_id(event_id, tenant_id)
        if not event:
            return None

        updated_event = self.repository.update_event(event, event_data)

        # Publish event
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self.event_publisher.publish(
                        event_type="calendar.event.updated",
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
                )
            else:
                loop.run_until_complete(
                    self.event_publisher.publish(
                        event_type="calendar.event.updated",
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
                )
        except Exception as e:
            logger.error(f"Failed to publish calendar.event.updated event: {e}")

        return updated_event

    def cancel_event(self, event_id: UUID, tenant_id: UUID) -> CalendarEvent | None:
        """Cancel an event."""
        event = self.repository.get_event_by_id(event_id, tenant_id)
        if not event:
            return None

        updated_event = self.repository.update_event(
            event, {"status": EventStatus.CANCELLED}
        )

        # Publish event
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self.event_publisher.publish(
                        event_type="calendar.event.cancelled",
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
                )
            else:
                loop.run_until_complete(
                    self.event_publisher.publish(
                        event_type="calendar.event.cancelled",
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
                )
        except Exception as e:
            logger.error(f"Failed to publish calendar.event.cancelled event: {e}")

        return updated_event

    def delete_event(self, event_id: UUID, tenant_id: UUID) -> bool:
        """Delete event."""
        event = self.repository.get_event_by_id(event_id, tenant_id)
        if not event:
            return False

        self.repository.delete_event(event)
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
        """Add reminder to event."""
        reminder_data["event_id"] = event_id
        reminder_data["tenant_id"] = tenant_id
        return self.repository.create_reminder(reminder_data)


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
            logger.warning(f"Event {reminder.event_id} not found or cancelled, skipping reminder")
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
                    event_type="calendar.event.reminder",
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
                    event_type="calendar.event.reminder",
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
                logger.info(f"Push notifications not yet implemented for reminder {reminder.id}")

            # Mark reminder as sent
            from datetime import UTC, datetime

            self.repository.update_reminder(
                reminder,
                {
                    "is_sent": True,
                    "sent_at": datetime.now(UTC),
                },
            )

            # Publish event
            try:
                await self.event_publisher.publish(
                    event_type="calendar.event.reminder.sent",
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
            except Exception as e:
                logger.error(f"Failed to publish calendar.event.reminder.sent event: {e}")

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

