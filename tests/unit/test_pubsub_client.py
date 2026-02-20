"""Unit tests for RedisStreamsClient."""

from unittest.mock import AsyncMock, patch

import pytest
import redis.asyncio as aioredis

from app.core.config_file import get_settings
from app.core.pubsub.client import RedisStreamsClient
from app.core.pubsub.errors import PubSubError

settings = get_settings()


@pytest.mark.asyncio
async def test_redis_client_initialization():
    """Test RedisStreamsClient initialization."""
    client = RedisStreamsClient(redis_url="redis://localhost:6379/0", password="")
    assert client.redis_url == "redis://localhost:6379/0"
    assert client.password == ""
    assert client._client is None


@pytest.mark.asyncio
async def test_redis_client_connection_success():
    """Test successful Redis connection."""
    client = RedisStreamsClient(redis_url="redis://localhost:6379/0", password="")

    with patch("app.core.pubsub.client.aioredis.from_url") as mock_from_url:
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_from_url.return_value = mock_redis

        redis_client = await client._get_client()

        assert redis_client == mock_redis
        mock_redis.ping.assert_called_once()


@pytest.mark.asyncio
async def test_redis_client_connection_failure():
    """Test Redis connection failure."""
    client = RedisStreamsClient(redis_url="redis://localhost:6379/0", password="")

    with patch("app.core.pubsub.client.aioredis.from_url") as mock_from_url:
        from redis.exceptions import ConnectionError as RedisConnectionError

        mock_from_url.side_effect = RedisConnectionError("Connection failed")

        with pytest.raises(PubSubError, match="Failed to connect to Redis"):
            await client._get_client()


@pytest.mark.asyncio
async def test_redis_client_connection_with_password():
    """Test Redis connection with password."""
    client = RedisStreamsClient(
        redis_url="redis://localhost:6379/0", password="testpass"
    )

    with patch("app.core.pubsub.client.aioredis.from_url") as mock_from_url:
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_from_url.return_value = mock_redis

        await client._get_client()

        # Verify password was passed
        call_kwargs = mock_from_url.call_args[1]
        assert call_kwargs.get("password") == "testpass"


@pytest.mark.asyncio
async def test_create_group_success():
    """Test successful group creation."""
    client = RedisStreamsClient(redis_url="redis://localhost:6379/0", password="")

    with patch.object(client, "connection") as mock_conn:
        mock_redis = AsyncMock()
        mock_redis.xgroup_create = AsyncMock()
        mock_conn.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
        mock_conn.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await client.create_group("test:stream", "test-group")

        assert result is True
        mock_redis.xgroup_create.assert_called_once_with(
            name="test:stream", groupname="test-group", id="0", mkstream=True
        )


@pytest.mark.asyncio
async def test_create_group_already_exists():
    """Test group creation when group already exists."""
    client = RedisStreamsClient(redis_url="redis://localhost:6379/0", password="")

    with patch.object(client, "connection") as mock_conn:
        mock_redis = AsyncMock()
        error = aioredis.ResponseError("BUSYGROUP Consumer Group name already exists")
        mock_redis.xgroup_create = AsyncMock(side_effect=error)
        mock_conn.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
        mock_conn.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await client.create_group("test:stream", "test-group")

        assert result is False


@pytest.mark.asyncio
async def test_get_stream_info():
    """Test getting stream information."""
    client = RedisStreamsClient(redis_url="redis://localhost:6379/0", password="")

    with patch.object(client, "connection") as mock_conn:
        mock_redis = AsyncMock()
        mock_redis.xinfo_stream = AsyncMock(
            return_value={"length": 10, "first-entry": "0-0"}
        )
        mock_conn.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
        mock_conn.return_value.__aexit__ = AsyncMock(return_value=False)

        info = await client.get_stream_info("test:stream")

        assert info["length"] == 10
        mock_redis.xinfo_stream.assert_called_once_with("test:stream")


@pytest.mark.asyncio
async def test_get_stream_info_not_found():
    """Test getting stream info when stream doesn't exist."""
    client = RedisStreamsClient(redis_url="redis://localhost:6379/0", password="")

    with patch.object(client, "connection") as mock_conn:
        mock_redis = AsyncMock()
        error = aioredis.ResponseError("no such key")
        mock_redis.xinfo_stream = AsyncMock(side_effect=error)
        mock_conn.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
        mock_conn.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(PubSubError, match="Stream 'test:stream' not found"):
            await client.get_stream_info("test:stream")


@pytest.mark.asyncio
async def test_get_group_info():
    """Test getting group information."""
    client = RedisStreamsClient(redis_url="redis://localhost:6379/0", password="")

    with patch.object(client, "connection") as mock_conn:
        mock_redis = AsyncMock()
        mock_redis.xinfo_groups = AsyncMock(
            return_value=[{"name": "test-group", "consumers": 2}]
        )
        mock_conn.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
        mock_conn.return_value.__aexit__ = AsyncMock(return_value=False)

        info = await client.get_group_info("test:stream", "test-group")

        assert info["name"] == "test-group"
        assert info["consumers"] == 2


@pytest.mark.asyncio
async def test_get_group_info_not_found():
    """Test getting group info when group doesn't exist."""
    client = RedisStreamsClient(redis_url="redis://localhost:6379/0", password="")

    with patch.object(client, "connection") as mock_conn:
        mock_redis = AsyncMock()
        mock_redis.xinfo_groups = AsyncMock(return_value=[])
        mock_conn.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
        mock_conn.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(PubSubError, match="Consumer group 'test-group' not found"):
            await client.get_group_info("test:stream", "test-group")


@pytest.mark.asyncio
async def test_get_pending_messages():
    """Test getting pending messages."""
    client = RedisStreamsClient(redis_url="redis://localhost:6379/0", password="")

    with patch.object(client, "connection") as mock_conn:
        mock_redis = AsyncMock()
        mock_redis.xpending_range = AsyncMock(
            return_value=[
                {
                    "message_id": "1000-0",
                    "consumer": "worker-1",
                    "time_since_delivered": 5000,
                }
            ]
        )
        mock_conn.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
        mock_conn.return_value.__aexit__ = AsyncMock(return_value=False)

        pending = await client.get_pending_messages(
            "test:stream", "test-group", count=10
        )

        assert len(pending) == 1
        assert pending[0]["message_id"] == "1000-0"
        mock_redis.xpending_range.assert_called_once_with(
            name="test:stream", groupname="test-group", min="-", max="+", count=10
        )


@pytest.mark.asyncio
async def test_connection_context_manager():
    """Test connection context manager."""
    client = RedisStreamsClient(redis_url="redis://localhost:6379/0", password="")

    with patch.object(client, "_get_client") as mock_get_client:
        mock_redis = AsyncMock()
        mock_get_client.return_value = mock_redis

        async with client.connection() as conn:
            assert conn == mock_redis


@pytest.mark.asyncio
async def test_connection_context_manager_error():
    """Test connection context manager with error."""
    client = RedisStreamsClient(redis_url="redis://localhost:6379/0", password="")

    with patch.object(client, "_get_client") as mock_get_client:
        from redis.exceptions import ConnectionError as RedisConnectionError

        mock_redis = AsyncMock()
        mock_redis.some_operation = AsyncMock(
            side_effect=RedisConnectionError("Connection lost")
        )
        mock_get_client.return_value = mock_redis

        with pytest.raises(PubSubError):
            async with client.connection() as conn:
                await conn.some_operation()


@pytest.mark.asyncio
async def test_close():
    """Test closing Redis connection."""
    client = RedisStreamsClient(redis_url="redis://localhost:6379/0", password="")

    with patch.object(client, "_get_client") as mock_get_client:
        mock_redis = AsyncMock()
        mock_redis.aclose = AsyncMock()
        mock_get_client.return_value = mock_redis
        client._client = mock_redis

        await client.close()

        assert client._client is None
        mock_redis.aclose.assert_called_once()
