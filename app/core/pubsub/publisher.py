"""Event publisher for Redis Streams."""

import logging
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis

from app.core.config_file import get_settings
from app.core.pubsub.client import RedisStreamsClient
from app.core.pubsub.errors import PublishError
from app.core.pubsub.models import Event, EventMetadata

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publisher for events to Redis Streams."""

    def __init__(self, client: RedisStreamsClient):
        """Initialize event publisher.

        Args:
            client: RedisStreamsClient instance
        """
        self.client = client
        self.settings = get_settings()

    def _determine_stream(self, event_type: str) -> str:
        """Determine which stream to use based on event type.

        Args:
            event_type: Event type (e.g., 'product.created', 'system.error')

        Returns:
            Stream name ('events:domain' or 'events:technical')
        """
        # Technical events: system.*, integration.*, audit.*, notification.*
        technical_prefixes = ["system.", "integration.", "audit.", "notification."]
        if any(event_type.startswith(prefix) for prefix in technical_prefixes):
            return self.settings.REDIS_STREAM_TECHNICAL
        return self.settings.REDIS_STREAM_DOMAIN

    async def publish(
        self,
        event_type: str,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        user_id: UUID | None = None,
        metadata: EventMetadata | None = None,
    ) -> str:
        """Publish an event to Redis Streams.

        Args:
            event_type: Event type in format '<module>.<action>'
            entity_type: Type of entity (e.g., 'product')
            entity_id: ID of the entity
            tenant_id: Tenant ID
            user_id: User ID (optional)
            metadata: Event metadata (optional)

        Returns:
            Message ID from Redis Streams

        Raises:
            PublishError: If publication fails
        """
        # Create event
        if metadata is None:
            metadata = EventMetadata(source="unknown", version="1.0")

        try:
            event = Event(
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                tenant_id=tenant_id,
                user_id=user_id,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            raise PublishError(f"Invalid event data: {e}") from e

        # Determine stream
        stream_name = self._determine_stream(event_type)

        # Publish to stream
        try:
            async with self.client.connection() as redis_client:
                event_dict = event.to_redis_dict()
                message_id = await redis_client.xadd(stream_name, event_dict)
                logger.info(
                    f"Published event '{event_type}' (ID: {event.event_id}) to stream '{stream_name}' "
                    f"(Redis ID: {message_id})"
                )
                return message_id
        except Exception as e:
            logger.error(f"Failed to publish event '{event_type}': {e}", exc_info=True)
            raise PublishError(f"Failed to publish event: {e}") from e









