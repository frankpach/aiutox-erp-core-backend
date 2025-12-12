"""Event consumer for notifications service."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config_file import get_settings
from app.core.db.session import get_db
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
            if event_type.startswith("notification.") or event_type.startswith("system."):
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

            logger.info(f"Notification sent for event {event_type} to user {recipient_id}")

        except Exception as e:
            logger.error(f"Error handling event {event.event_type}: {e}", exc_info=True)
            # Don't re-raise - we want to continue processing other events
            # The error will be logged and can be monitored

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

