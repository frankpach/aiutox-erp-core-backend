"""Event consumer for notifications service."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config_file import get_settings
from app.core.notifications.service import NotificationService
from app.core.pubsub import EventConsumer, RedisStreamsClient
from app.core.pubsub.models import Event

logger = logging.getLogger(__name__)


class NotificationEventConsumer:
    """Consumer for events that trigger notifications."""

    def __init__(self, db: Session, consumer: EventConsumer | None = None):
        """Initialize notification event consumer.

        Args:
            db: Database session
            consumer: EventConsumer instance (created if not provided)
        """
        self.db = db
        self.settings = get_settings()

        # Create consumer if not provided
        if consumer is None:
            client = RedisStreamsClient(
                redis_url=self.settings.REDIS_URL, password=self.settings.REDIS_PASSWORD
            )
            consumer = EventConsumer(client=client)

        self.consumer = consumer
        self.notification_service = NotificationService(db)
        self._running = False

    async def start(self):
        """Start consuming events and sending notifications."""
        if self._running:
            logger.warning("Notification consumer is already running")
            return

        self._running = True

        # Subscribe to domain events
        # Event types that should trigger notifications can be configured
        # For now, we'll subscribe to all events and filter in the callback
        await self.consumer.subscribe(
            group_name="notifications-service",
            consumer_name="notifications-consumer-1",
            event_types=[],  # Empty list = all events
            callback=self._handle_event,
            stream_name=self.settings.REDIS_STREAM_DOMAIN,
        )

        logger.info("Notification event consumer started")

    async def stop(self):
        """Stop consuming events."""
        self._running = False
        # EventConsumer doesn't have a stop method, but we can mark as not running
        logger.info("Notification event consumer stopped")

    async def _handle_event(self, event: Event) -> None:
        """Handle an event and send notification if needed.

        Args:
            event: Event from the bus
        """
        try:
            # Map event types to notification channels
            # This is a simple mapping - can be enhanced with configuration
            event_type = event.event_type

            # Skip technical events and notification events themselves
            if event_type.startswith("notification.") or event_type.startswith(
                "system."
            ):
                return

            # Handle task-specific events with dedicated handlers
            if event_type == "task.assigned":
                await self._handle_task_assigned(event)
                return
            elif event_type == "task.status_changed":
                await self._handle_task_status_changed(event)
                return
            elif event_type == "task.due_soon":
                await self._handle_task_due_soon(event)
                return
            elif event_type == "task.overdue":
                await self._handle_task_overdue(event)
                return
            elif event_type == "task.created":
                await self._handle_task_created(event)
                return
            elif event_type == "task.completed":
                await self._handle_task_completed(event)
                return

            # Determine which users should receive notifications for this event
            # For now, we'll use a simple rule: notify the user who triggered the event
            # In a real system, this would be more sophisticated (e.g., based on automation rules)

            # Get recipient - for now, use the user_id from the event
            # In production, this would be determined by business rules
            recipient_id = event.user_id
            if not recipient_id:
                logger.debug(f"No user_id in event {event_type}, skipping notification")
                return

            # Determine channels based on event type
            # Default to in-app notifications
            channels = ["in-app"]

            # For certain events, also send email
            if event_type in [
                "product.created",
                "product.updated",
                "inventory.stock_low",
                "order.created",
            ]:
                channels.append("email")

            # Send notification
            await self.notification_service.send(
                event_type=event_type,
                recipient_id=recipient_id,
                channels=channels,
                data=self._extract_notification_data(event),
                tenant_id=event.tenant_id,
            )

            logger.info(
                f"Notification sent for event {event_type} to user {recipient_id}"
            )

        except Exception as e:
            logger.error(f"Error handling event {event.event_type}: {e}", exc_info=True)
            # Don't re-raise - we want to continue processing other events
            # The error will be logged and can be monitored

    async def _handle_task_assigned(self, event: Event) -> None:
        """Handle task.assigned event."""
        metadata = event.metadata.additional_data if event.metadata else {}
        assigned_to_id = metadata.get("assigned_to_id")

        if not assigned_to_id:
            return

        await self.notification_service.send(
            event_type="task.assigned",
            recipient_id=UUID(assigned_to_id),
            channels=["in-app", "email"],
            data={
                "task_title": metadata.get("task_title", "Sin título"),
                "assigned_by_id": metadata.get("assigned_by_id"),
                "due_date": metadata.get("due_date"),
            },
            tenant_id=event.tenant_id,
        )
        logger.info(f"Sent task.assigned notification to {assigned_to_id}")

    async def _handle_task_status_changed(self, event: Event) -> None:
        """Handle task.status_changed event."""
        metadata = event.metadata.additional_data if event.metadata else {}

        # Notify task creator and assigned user
        recipients = []
        if event.user_id:
            recipients.append(event.user_id)

        for recipient_id in recipients:
            await self.notification_service.send(
                event_type="task.status_changed",
                recipient_id=recipient_id,
                channels=["in-app"],
                data={
                    "task_title": metadata.get("task_title", "Sin título"),
                    "old_status": metadata.get("old_status"),
                    "new_status": metadata.get("new_status"),
                    "changed_by_id": metadata.get("changed_by_id"),
                },
                tenant_id=event.tenant_id,
            )
        logger.info("Sent task.status_changed notification")

    async def _handle_task_due_soon(self, event: Event) -> None:
        """Handle task.due_soon event."""
        metadata = event.metadata.additional_data if event.metadata else {}
        assigned_to_id = metadata.get("assigned_to_id")
        created_by_id = metadata.get("created_by_id")

        # Notify assigned user and creator
        recipients = []
        if assigned_to_id:
            recipients.append(UUID(assigned_to_id))
        if created_by_id and created_by_id != assigned_to_id:
            recipients.append(UUID(created_by_id))

        for recipient_id in recipients:
            await self.notification_service.send(
                event_type="task.due_soon",
                recipient_id=recipient_id,
                channels=["in-app", "email"],
                data={
                    "task_title": metadata.get("task_title", "Sin título"),
                    "due_date": metadata.get("due_date"),
                    "window": metadata.get("window", "soon"),
                },
                tenant_id=event.tenant_id,
            )
        logger.info(f"Sent task.due_soon notification ({metadata.get('window')})")

    async def _handle_task_overdue(self, event: Event) -> None:
        """Handle task.overdue event."""
        metadata = event.metadata.additional_data if event.metadata else {}
        assigned_to_id = metadata.get("assigned_to_id")
        created_by_id = metadata.get("created_by_id")

        # Notify assigned user and creator
        recipients = []
        if assigned_to_id:
            recipients.append(UUID(assigned_to_id))
        if created_by_id and created_by_id != assigned_to_id:
            recipients.append(UUID(created_by_id))

        for recipient_id in recipients:
            await self.notification_service.send(
                event_type="task.overdue",
                recipient_id=recipient_id,
                channels=["in-app", "email"],
                data={
                    "task_title": metadata.get("task_title", "Sin título"),
                    "due_date": metadata.get("due_date"),
                    "days_overdue": metadata.get("days_overdue", 0),
                },
                tenant_id=event.tenant_id,
            )
        logger.info("Sent task.overdue notification")

    async def _handle_task_created(self, event: Event) -> None:
        """Handle task.created event."""
        metadata = event.metadata.additional_data if event.metadata else {}
        assigned_to_id = metadata.get("assigned_to_id")

        # Only notify if task is assigned to someone other than creator
        if assigned_to_id and str(event.user_id) != assigned_to_id:
            await self.notification_service.send(
                event_type="task.created",
                recipient_id=UUID(assigned_to_id),
                channels=["in-app"],
                data={
                    "task_title": metadata.get("title", "Sin título"),
                },
                tenant_id=event.tenant_id,
            )
            logger.info("Sent task.created notification")

    async def _handle_task_completed(self, event: Event) -> None:
        """Handle task.completed event."""
        metadata = event.metadata.additional_data if event.metadata else {}

        # Notify task creator
        if event.user_id:
            await self.notification_service.send(
                event_type="task.completed",
                recipient_id=event.user_id,
                channels=["in-app"],
                data={
                    "task_title": metadata.get("task_title", "Sin título"),
                },
                tenant_id=event.tenant_id,
            )
            logger.info("Sent task.completed notification")

    def _extract_notification_data(self, event: Event) -> dict[str, Any]:
        """Extract data from event for notification template rendering.

        Args:
            event: Event from the bus

        Returns:
            Dictionary with data for template rendering
        """
        data = {
            "event_type": event.event_type,
            "entity_type": event.entity_type,
            "entity_id": str(event.entity_id),
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }

        # Add metadata if available
        if event.metadata and event.metadata.additional_data:
            data.update(event.metadata.additional_data)

        return data
