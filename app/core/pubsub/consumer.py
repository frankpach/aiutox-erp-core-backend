"""Event consumer for Redis Streams."""

import asyncio
import logging
from typing import Any, Awaitable, Callable

import redis.asyncio as aioredis

from app.core.config_file import get_settings
from app.core.pubsub.client import RedisStreamsClient
from app.core.pubsub.errors import ConsumeError
from app.core.pubsub.groups import ensure_group_exists
from app.core.pubsub.models import Event
from app.core.pubsub.retry import RetryHandler

logger = logging.getLogger(__name__)


class EventConsumer:
    """Consumer for events from Redis Streams."""

    def __init__(self, client: RedisStreamsClient):
        """Initialize event consumer.

        Args:
            client: RedisStreamsClient instance
        """
        self.client = client
        self.settings = get_settings()
        self._running = False
        self._tasks: list[asyncio.Task] = []

    async def subscribe(
        self,
        group_name: str,
        consumer_name: str,
        event_types: list[str],
        callback: Callable[[Event], Awaitable[None]],
        stream_name: str | None = None,
        start_id: str = "0",
        recreate_group: bool = False,
    ):
        """Subscribe to events from a stream.

        Args:
            group_name: Name of the consumer group
            consumer_name: Name of this consumer instance
            event_types: List of event types to subscribe to (empty list = all events)
            callback: Async function to call for each event
            stream_name: Stream name (default: events:domain)
            start_id: Starting ID for the consumer group. Use "$" to read only new messages
                     (useful for tests), "0" to read all messages (default)
            recreate_group: If True, delete and recreate the group if it already exists
                           (useful for tests to ensure correct start_id)
        """
        if stream_name is None:
            stream_name = self.settings.REDIS_STREAM_DOMAIN

        # Ensure group exists with specified start_id
        try:
            await ensure_group_exists(self.client, stream_name, group_name, start_id=start_id, recreate_if_exists=recreate_group)
        except Exception as e:
            logger.error(f"Failed to ensure group exists: {e}")
            raise ConsumeError(f"Failed to setup consumer group: {e}") from e

        # Start consumption loop
        self._running = True
        task = asyncio.create_task(
            self._consume_loop(stream_name, group_name, consumer_name, event_types, callback)
        )
        self._tasks.append(task)
        logger.info(
            f"Started consumer '{consumer_name}' in group '{group_name}' "
            f"for stream '{stream_name}' (event_types: {event_types or 'all'})"
        )

    async def _consume_loop(
        self,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        event_types: list[str],
        callback: Callable[[Event], Awaitable[None]],
    ):
        """Main consumption loop."""
        retry_handler = RetryHandler(max_attempts=5)

        while self._running:
            try:
                async with self.client.connection() as redis_client:
                    # Read messages from stream
                    messages = await redis_client.xreadgroup(
                        groupname=group_name,
                        consumername=consumer_name,
                        streams={stream_name: ">"},
                        count=10,
                        block=1000,  # Block for 1 second
                    )

                    if not messages:
                        continue

                    # Process each message
                    for stream, message_list in messages:
                        for message_id, data in message_list:
                            try:
                                # Parse event - ensure data is a proper dict
                                # Redis returns data as dict when decode_responses=True
                                # Handle both dict and list/tuple formats from Redis
                                if isinstance(data, dict):
                                    event_data = data
                                elif isinstance(data, (list, tuple)):
                                    # Convert list of tuples to dict (Redis sometimes returns this format)
                                    event_data = dict(data)
                                else:
                                    # Fallback: try to convert to dict
                                    event_data = dict(data) if hasattr(data, 'items') else {}

                                event = Event.from_redis_dict(event_data)

                                # Filter by event types if specified
                                if event_types and event.event_type not in event_types:
                                    # ACK even if filtered out
                                    await redis_client.xack(stream_name, group_name, message_id)
                                    continue

                                # Process event with retry
                                await retry_handler.retry_with_backoff(
                                    lambda: callback(event),
                                    operation_name=f"Processing event {event.event_id}",
                                )

                                # ACK message after successful processing
                                await redis_client.xack(stream_name, group_name, message_id)
                                logger.debug(
                                    f"Processed and ACKed event '{event.event_type}' "
                                    f"(ID: {event.event_id}, Redis ID: {message_id})"
                                )

                            except Exception as e:
                                logger.error(
                                    f"Failed to process message {message_id}: {e}",
                                    exc_info=True,
                                )
                                # After retries exhausted, move to failed stream
                                try:
                                    await self._move_to_failed_stream(
                                        redis_client, stream_name, message_id, data, str(e)
                                    )
                                    # ACK to remove from pending
                                    await redis_client.xack(stream_name, group_name, message_id)
                                except Exception as move_error:
                                    logger.error(
                                        f"Failed to move message to failed stream: {move_error}",
                                        exc_info=True,
                                    )

            except Exception as e:
                logger.error(f"Error in consumption loop: {e}", exc_info=True)
                # Wait before retrying
                await asyncio.sleep(1)

    async def _move_to_failed_stream(
        self,
        redis_client: aioredis.Redis,
        stream_name: str,
        message_id: str,
        original_data: dict[str, str],
        error_info: str,
    ):
        """Move a failed message to the failed events stream."""
        failed_data = original_data.copy()
        failed_data["original_stream"] = stream_name
        failed_data["original_message_id"] = message_id
        failed_data["error_info"] = error_info
        # Get current time - use asyncio loop time if available, otherwise use time.time()
        try:
            loop = asyncio.get_running_loop()
            failed_data["failed_at"] = str(loop.time())
        except RuntimeError:
            import time
            failed_data["failed_at"] = str(time.time())

        await redis_client.xadd(self.settings.REDIS_STREAM_FAILED, failed_data)
        logger.warning(
            f"Moved failed message {message_id} from '{stream_name}' to '{self.settings.REDIS_STREAM_FAILED}'"
        )

    async def acknowledge(self, stream_name: str, group_name: str, message_id: str):
        """Acknowledge a message as processed.

        Args:
            stream_name: Name of the stream
            group_name: Name of the consumer group
            message_id: ID of the message to acknowledge
        """
        try:
            async with self.client.connection() as redis_client:
                await redis_client.xack(stream_name, group_name, message_id)
                logger.debug(f"Acknowledged message {message_id} in group {group_name}")
        except Exception as e:
            logger.error(f"Failed to acknowledge message: {e}")
            raise ConsumeError(f"Failed to acknowledge message: {e}") from e

    async def claim_pending_messages(
        self,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        min_idle_time: int = 60000,  # 60 seconds in milliseconds
        count: int = 10,
    ) -> list[tuple[str, dict[str, str]]]:
        """Claim pending messages from other consumers.

        Args:
            stream_name: Name of the stream
            group_name: Name of the consumer group
            consumer_name: Name of this consumer
            min_idle_time: Minimum idle time in milliseconds
            count: Maximum number of messages to claim

        Returns:
            List of (message_id, data) tuples
        """
        try:
            async with self.client.connection() as redis_client:
                # Get pending messages
                pending = await redis_client.xpending_range(
                    name=stream_name,
                    groupname=group_name,
                    min="-",
                    max="+",
                    count=count,
                )

                if not pending:
                    return []

                # Claim messages
                message_ids = [msg["message_id"] for msg in pending]
                claimed = await redis_client.xclaim(
                    name=stream_name,
                    groupname=group_name,
                    consumername=consumer_name,
                    min_idle_time=min_idle_time,
                    message_ids=message_ids,
                )

                result = []
                for msg_id, data in claimed:
                    result.append((msg_id, dict(data)))

                if result:
                    logger.info(
                        f"Claimed {len(result)} pending messages for consumer '{consumer_name}'"
                    )

                return result
        except Exception as e:
            logger.error(f"Failed to claim pending messages: {e}")
            raise ConsumeError(f"Failed to claim pending messages: {e}") from e

    async def stop(self):
        """Stop the consumer."""
        self._running = False

        if self._tasks:
            # Cancel all tasks explicitly before waiting
            for task in self._tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to finish (they should handle CancelledError)
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()

        logger.info("Stopped event consumer")


