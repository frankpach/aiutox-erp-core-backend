"""Redis Streams client wrapper."""

import logging
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as aioredis
from redis.exceptions import ConnectionError, RedisError

from app.core.pubsub.errors import PubSubError

logger = logging.getLogger(__name__)


class RedisStreamsClient:
    """Wrapper for Redis client with Streams-specific methods."""

    def __init__(self, redis_url: str, password: str = ""):
        """Initialize Redis client.

        Args:
            redis_url: Redis connection URL (e.g., 'redis://localhost:6379/0')
            password: Redis password (optional)
        """
        self.redis_url = redis_url
        self.password = password
        self._client: aioredis.Redis | None = None

    async def _get_client(self) -> aioredis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            try:
                # Parse URL and add password if provided
                # Note: redis-py's from_url can handle password in URL or separately
                # We'll pass password as a parameter if not in URL
                connection_kwargs = {}
                if self.password and "@" not in self.redis_url:
                    # Password not in URL, add it to connection kwargs
                    connection_kwargs["password"] = self.password

                self._client = aioredis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    **connection_kwargs,
                )
                # Test connection
                await self._client.ping()
                logger.info("Connected to Redis successfully")
            except (ConnectionError, RedisError) as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise PubSubError(f"Failed to connect to Redis: {e}") from e

        return self._client

    @asynccontextmanager
    async def connection(self):
        """Context manager for Redis connection."""
        client = await self._get_client()
        try:
            yield client
        except (ConnectionError, RedisError) as e:
            logger.error(f"Redis connection error: {e}")
            # Reset client to force reconnection
            if self._client:
                await self._client.aclose()
                self._client = None
            raise PubSubError(f"Redis connection error: {e}") from e

    async def create_group(self, stream_name: str, group_name: str, start_id: str = "0") -> bool:
        """Create a consumer group for a stream.

        Args:
            stream_name: Name of the stream
            group_name: Name of the consumer group
            start_id: Starting ID for the group (default: '0' for all messages)

        Returns:
            True if group was created, False if it already exists
        """
        async with self.connection() as client:
            try:
                await client.xgroup_create(
                    name=stream_name, groupname=group_name, id=start_id, mkstream=True
                )
                logger.info(f"Created consumer group '{group_name}' for stream '{stream_name}'")
                return True
            except aioredis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    logger.debug(f"Consumer group '{group_name}' already exists for stream '{stream_name}'")
                    return False
                raise PubSubError(f"Failed to create consumer group: {e}") from e

    async def get_stream_info(self, stream_name: str) -> dict[str, Any]:
        """Get information about a stream.

        Args:
            stream_name: Name of the stream

        Returns:
            Dictionary with stream information
        """
        async with self.connection() as client:
            try:
                info = await client.xinfo_stream(stream_name)
                return dict(info)
            except aioredis.ResponseError as e:
                if "no such key" in str(e).lower():
                    raise PubSubError(f"Stream '{stream_name}' not found") from e
                raise PubSubError(f"Failed to get stream info: {e}") from e

    async def get_group_info(self, stream_name: str, group_name: str) -> dict[str, Any]:
        """Get information about a consumer group.

        Args:
            stream_name: Name of the stream
            group_name: Name of the consumer group

        Returns:
            Dictionary with group information
        """
        async with self.connection() as client:
            try:
                groups = await client.xinfo_groups(stream_name)
                for group in groups:
                    if group.get("name") == group_name:
                        return dict(group)
                raise PubSubError(f"Consumer group '{group_name}' not found in stream '{stream_name}'")
            except aioredis.ResponseError as e:
                if "no such key" in str(e).lower():
                    raise PubSubError(f"Stream '{stream_name}' not found") from e
                raise PubSubError(f"Failed to get group info: {e}") from e

    async def get_pending_messages(
        self, stream_name: str, group_name: str, count: int = 10
    ) -> list[dict[str, Any]]:
        """Get pending messages for a consumer group.

        Args:
            stream_name: Name of the stream
            group_name: Name of the consumer group
            count: Maximum number of messages to return

        Returns:
            List of pending messages
        """
        async with self.connection() as client:
            try:
                pending = await client.xpending_range(
                    name=stream_name, groupname=group_name, min="-", max="+", count=count
                )
                return [dict(msg) for msg in pending]
            except aioredis.ResponseError as e:
                if "no such key" in str(e).lower():
                    raise PubSubError(f"Stream '{stream_name}' not found") from e
                raise PubSubError(f"Failed to get pending messages: {e}") from e

    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Closed Redis connection")










