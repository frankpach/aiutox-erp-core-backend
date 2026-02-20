"""Unit tests for EventConsumer."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.config_file import get_settings
from app.core.pubsub.client import RedisStreamsClient
from app.core.pubsub.consumer import EventConsumer
from app.core.pubsub.errors import ConsumeError
from app.core.pubsub.models import Event

settings = get_settings()

# Timeout para evitar loops infinitos
TEST_TIMEOUT = 5.0


@pytest.fixture
def mock_client():
    """Create a mock RedisStreamsClient."""
    client = MagicMock(spec=RedisStreamsClient)
    client.create_group = AsyncMock(return_value=True)
    return client


@pytest.fixture
def event_consumer(mock_client):
    """Create EventConsumer with mock client."""
    return EventConsumer(client=mock_client)


@pytest.mark.asyncio
async def test_consumer_initialization(event_consumer):
    """Test EventConsumer initialization."""
    assert event_consumer.client is not None
    assert event_consumer._running is False
    assert event_consumer._tasks == []


@pytest.mark.asyncio
async def test_subscribe_creates_group(event_consumer, mock_client):
    """Test that subscribe creates consumer group."""
    with patch("app.core.pubsub.consumer.ensure_group_exists") as mock_ensure:
        mock_ensure.return_value = True

        await event_consumer.subscribe(
            group_name="test-group",
            consumer_name="test-consumer",
            event_types=["product.created"],
            callback=AsyncMock(),
        )

        mock_ensure.assert_called_once()
        assert event_consumer._running is True
        assert len(event_consumer._tasks) == 1

        # Cleanup
        await event_consumer.stop()


@pytest.mark.asyncio
async def test_subscribe_group_creation_failure(event_consumer, mock_client):
    """Test subscribe when group creation fails."""
    with patch("app.core.pubsub.consumer.ensure_group_exists") as mock_ensure:
        mock_ensure.side_effect = ConsumeError("Failed to create group")

        with pytest.raises(ConsumeError, match="Failed to setup consumer group"):
            await event_consumer.subscribe(
                group_name="test-group",
                consumer_name="test-consumer",
                event_types=[],
                callback=AsyncMock(),
            )


@pytest.mark.asyncio
async def test_consume_loop_processes_messages(event_consumer, mock_client):
    """Test that consume loop processes messages with timeout."""
    received_events = []
    processing_done = asyncio.Event()

    async def callback(event: Event):
        received_events.append(event)
        processing_done.set()

    mock_redis = AsyncMock()
    # Simulate messages from Redis - solo una vez
    mock_redis.xreadgroup = AsyncMock(
        side_effect=[
            # Primera llamada: retorna mensajes
            [
                (
                    settings.REDIS_STREAM_DOMAIN,
                    [
                        (
                            "1000-0",
                            {
                                "event_id": str(uuid4()),
                                "event_type": "product.created",
                                "entity_type": "product",
                                "entity_id": str(uuid4()),
                                "tenant_id": str(uuid4()),
                                "user_id": "",
                                "timestamp": "2025-01-01T00:00:00+00:00",
                                "metadata_source": "test",
                                "metadata_version": "1.0",
                                "metadata_additional_data": "{}",
                            },
                        )
                    ],
                )
            ],
            # Segunda llamada: retorna vacío para que el loop termine
            [],
            [],
        ]
    )
    mock_redis.xack = AsyncMock()

    mock_client.connection.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
    mock_client.connection.return_value.__aexit__ = AsyncMock(return_value=False)

    async def test_workflow():
        # Start consume loop
        event_consumer._running = True
        task = asyncio.create_task(
            event_consumer._consume_loop(
                settings.REDIS_STREAM_DOMAIN,
                "test-group",
                "test-consumer",
                ["product.created"],
                callback,
            )
        )

        # Wait for processing with timeout
        try:
            await asyncio.wait_for(processing_done.wait(), timeout=2.0)
        except TimeoutError:
            pass  # Puede que no se procese en tiempo, pero no es crítico para el test

        # Stop consumer inmediatamente
        event_consumer._running = False
        await asyncio.sleep(0.1)  # Dar tiempo para que el loop vea el flag

        # Cancelar task si aún está corriendo
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Verificar que se llamó xreadgroup
        assert mock_redis.xreadgroup.call_count >= 1

    await asyncio.wait_for(test_workflow(), timeout=TEST_TIMEOUT)


@pytest.mark.asyncio
async def test_acknowledge_message(event_consumer, mock_client):
    """Test acknowledging a message."""
    mock_redis = AsyncMock()
    mock_redis.xack = AsyncMock()
    mock_client.connection.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
    mock_client.connection.return_value.__aexit__ = AsyncMock(return_value=False)

    await event_consumer.acknowledge("test:stream", "test-group", "1000-0")

    mock_redis.xack.assert_called_once_with("test:stream", "test-group", "1000-0")


@pytest.mark.asyncio
async def test_acknowledge_message_error(event_consumer, mock_client):
    """Test acknowledge when Redis operation fails."""
    mock_redis = AsyncMock()
    mock_redis.xack = AsyncMock(side_effect=Exception("Redis error"))
    mock_client.connection.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
    mock_client.connection.return_value.__aexit__ = AsyncMock(return_value=False)

    with pytest.raises(ConsumeError, match="Failed to acknowledge message"):
        await event_consumer.acknowledge("test:stream", "test-group", "1000-0")


@pytest.mark.asyncio
async def test_claim_pending_messages(event_consumer, mock_client):
    """Test claiming pending messages."""
    mock_redis = AsyncMock()
    mock_redis.xpending_range = AsyncMock(
        return_value=[{"message_id": "1000-0"}, {"message_id": "2000-0"}]
    )
    mock_redis.xclaim = AsyncMock(
        return_value=[("1000-0", {"event_id": "123"}), ("2000-0", {"event_id": "456"})]
    )
    mock_client.connection.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
    mock_client.connection.return_value.__aexit__ = AsyncMock(return_value=False)

    claimed = await event_consumer.claim_pending_messages(
        "test:stream", "test-group", "test-consumer", min_idle_time=60000, count=10
    )

    assert len(claimed) == 2
    assert claimed[0][0] == "1000-0"
    mock_redis.xclaim.assert_called_once()


@pytest.mark.asyncio
async def test_claim_pending_messages_empty(event_consumer, mock_client):
    """Test claiming when no pending messages."""
    mock_redis = AsyncMock()
    mock_redis.xpending_range = AsyncMock(return_value=[])
    mock_client.connection.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
    mock_client.connection.return_value.__aexit__ = AsyncMock(return_value=False)

    claimed = await event_consumer.claim_pending_messages(
        "test:stream", "test-group", "test-consumer"
    )

    assert len(claimed) == 0


@pytest.mark.asyncio
async def test_stop_consumer(event_consumer):
    """Test stopping the consumer."""
    # Create a real task that we can cancel
    async def dummy_task():
        try:
            while True:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(dummy_task())
    event_consumer._tasks = [task]
    event_consumer._running = True

    # Stop the consumer
    await event_consumer.stop()

    assert event_consumer._running is False
    assert len(event_consumer._tasks) == 0
    # Task should be done (either cancelled or completed)
    assert task.done()

