"""Trigger handler for automation rules."""

import logging
from collections.abc import Awaitable, Callable

from app.core.config_file import get_settings
from app.core.pubsub import EventConsumer
from app.core.pubsub.client import RedisStreamsClient
from app.core.pubsub.models import Event

logger = logging.getLogger(__name__)

settings = get_settings()


class TriggerHandler:
    """Handler for rule triggers (events and time)."""

    def __init__(self, event_consumer: EventConsumer | None = None):
        """Initialize trigger handler.

        Args:
            event_consumer: EventConsumer instance (optional, will create if not provided)
        """
        if event_consumer is None:
            client = RedisStreamsClient(
                redis_url=settings.REDIS_URL, password=settings.REDIS_PASSWORD
            )
            self.event_consumer = EventConsumer(client)
        else:
            self.event_consumer = event_consumer

    async def subscribe_to_event(
        self,
        event_type: str,
        callback: Callable[[Event], Awaitable[None]],
        group_name: str = "automation",
        consumer_name: str = "automation_engine",
    ) -> None:
        """Subscribe to an event type.

        Args:
            event_type: Event type to subscribe to (e.g., 'product.created')
            callback: Async function to call when event is received
            group_name: Consumer group name
            consumer_name: Consumer instance name
        """
        await self.event_consumer.subscribe(
            group_name=group_name,
            consumer_name=consumer_name,
            event_types=[event_type],
            callback=callback,
        )
        logger.info(f"Subscribed to event type: {event_type}")

    async def subscribe_to_multiple_events(
        self,
        event_types: list[str],
        callback: Callable[[Event], Awaitable[None]],
        group_name: str = "automation",
        consumer_name: str = "automation_engine",
    ) -> None:
        """Subscribe to multiple event types.

        Args:
            event_types: List of event types to subscribe to
            callback: Async function to call when any event is received
            group_name: Consumer group name
            consumer_name: Consumer instance name
        """
        # Subscribe to each event type separately
        for event_type in event_types:
            await self.subscribe_to_event(
                event_type, callback, group_name, consumer_name
            )

    async def stop(self) -> None:
        """Stop the event consumer."""
        await self.event_consumer.stop()
        logger.info("Stopped trigger handler")
