"""Consumer group management utilities."""

import logging

from app.core.pubsub.client import RedisStreamsClient
from app.core.pubsub.errors import PubSubError

logger = logging.getLogger(__name__)


async def ensure_group_exists(
    client: RedisStreamsClient, stream_name: str, group_name: str, start_id: str = "0"
) -> bool:
    """Ensure a consumer group exists for a stream.

    Args:
        client: RedisStreamsClient instance
        stream_name: Name of the stream
        group_name: Name of the consumer group
        start_id: Starting ID for the group (default: '0' for all messages)

    Returns:
        True if group was created, False if it already existed
    """
    try:
        return await client.create_group(stream_name, group_name, start_id)
    except PubSubError as e:
        logger.error(f"Failed to ensure group exists: {e}")
        raise


async def get_or_create_group(
    client: RedisStreamsClient, stream_name: str, group_name: str, start_id: str = "0"
) -> bool:
    """Get or create a consumer group.

    This is an alias for ensure_group_exists for clarity.

    Args:
        client: RedisStreamsClient instance
        stream_name: Name of the stream
        group_name: Name of the consumer group
        start_id: Starting ID for the group (default: '0' for all messages)

    Returns:
        True if group was created, False if it already existed
    """
    return await ensure_group_exists(client, stream_name, group_name, start_id)









