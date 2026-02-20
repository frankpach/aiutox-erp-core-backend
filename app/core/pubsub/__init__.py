"""Pub-Sub module for event bus based on Redis Streams and Redis Pub/Sub."""

from app.core.pubsub import payloads, topics
from app.core.pubsub.client import RedisStreamsClient
from app.core.pubsub.consumer import EventConsumer
from app.core.pubsub.errors import (
    ConsumeError,
    GroupNotFoundError,
    PublishError,
    PubSubError,
    StreamNotFoundError,
)
from app.core.pubsub.models import Event, EventMetadata
from app.core.pubsub.publisher import EventPublisher
from app.core.pubsub.redis_event_bus import RedisEventBus, get_redis_event_bus

__all__ = [
    "RedisStreamsClient",
    "EventPublisher",
    "EventConsumer",
    "Event",
    "EventMetadata",
    "PubSubError",
    "StreamNotFoundError",
    "GroupNotFoundError",
    "PublishError",
    "ConsumeError",
    "get_event_publisher",
    "RedisEventBus",
    "get_redis_event_bus",
    "topics",
    "payloads",
]


def get_event_publisher() -> EventPublisher:
    """Dependency function to get EventPublisher instance."""
    from app.core.config_file import get_settings
    from app.core.pubsub.client import RedisStreamsClient

    settings = get_settings()
    client = RedisStreamsClient(
        redis_url=settings.REDIS_URL, password=settings.REDIS_PASSWORD
    )
    return EventPublisher(client=client)
