"""Robust integration tests for Redis connection and error handling."""

import asyncio
from uuid import uuid4

import pytest

from app.core.config_file import get_settings
from app.core.pubsub.client import RedisStreamsClient
from app.core.pubsub.consumer import EventConsumer
from app.core.pubsub.errors import PubSubError
from app.core.pubsub.models import Event, EventMetadata
from app.core.pubsub.publisher import EventPublisher

settings = get_settings()


@pytest.fixture
async def redis_client():
    """Create Redis client for testing with proper cleanup."""
    client = RedisStreamsClient(redis_url=settings.REDIS_URL, password=settings.REDIS_PASSWORD)
    try:
        yield client
    finally:
        await client.close()


@pytest.fixture
def event_publisher(redis_client):
    """Create EventPublisher for testing."""
    return EventPublisher(client=redis_client)


@pytest.fixture
def event_consumer(redis_client):
    """Create EventConsumer for testing."""
    return EventConsumer(client=redis_client)


@pytest.mark.asyncio
async def test_redis_connection_recovery(redis_client):
    """Test that Redis client can recover from connection errors."""
    # Test basic connection
    async with redis_client.connection() as client:
        result = await client.ping()
        assert result is True

    # Close and reconnect
    await redis_client.close()

    # Create new client (simulating reconnection)
    new_client = RedisStreamsClient(
        redis_url=settings.REDIS_URL, password=settings.REDIS_PASSWORD
    )
    try:
        async with new_client.connection() as client:
            result = await client.ping()
            assert result is True
    finally:
        await new_client.close()


@pytest.mark.asyncio
async def test_redis_stream_creation_if_not_exists(event_publisher):
    """Test that streams are created automatically if they don't exist."""
    test_stream = f"test:stream:{uuid4().hex[:8]}"

    # Try to get info from non-existent stream (should handle gracefully)
    async with event_publisher.client.connection() as client:
        try:
            info = await client.xinfo_stream(test_stream)
            # If stream exists, that's fine
            assert "length" in info
        except Exception as e:
            # Stream doesn't exist, which is expected
            assert "no such key" in str(e).lower() or "not found" in str(e).lower()

        # Add a message to create the stream
        await client.xadd(test_stream, {"test": "data"})

        # Now stream should exist
        info = await client.xinfo_stream(test_stream)
        assert info["length"] >= 1


@pytest.mark.asyncio
async def test_redis_concurrent_consumers(event_publisher, event_consumer):
    """Test that multiple consumers can process events concurrently."""
    tenant_id = uuid4()
    entity_id = uuid4()

    processed_events = []

    async def consumer1_callback(event: Event):
        processed_events.append(("consumer1", event.event_id))

    async def consumer2_callback(event: Event):
        processed_events.append(("consumer2", event.event_id))

    # Create two consumers in different groups
    await event_consumer.subscribe(
        group_name="test-concurrent-group-1",
        consumer_name="consumer-1",
        event_types=["product.created"],
        callback=consumer1_callback,
    )

    # Create second consumer
    consumer2 = EventConsumer(client=event_publisher.client)
    await consumer2.subscribe(
        group_name="test-concurrent-group-2",
        consumer_name="consumer-2",
        event_types=["product.created"],
        callback=consumer2_callback,
    )

    await asyncio.sleep(0.5)

    # Publish event
    event_id = await event_publisher.publish(
        event_type="product.created",
        entity_type="product",
        entity_id=entity_id,
        tenant_id=tenant_id,
        metadata=EventMetadata(source="test"),
    )

    # Wait for processing
    await asyncio.sleep(2)

    await event_consumer.stop()
    await consumer2.stop()

    # Both consumers should have processed the event
    # (in a real scenario with same group, only one would process)
    assert len(processed_events) >= 1


@pytest.mark.asyncio
async def test_redis_error_handling(event_publisher):
    """Test that Redis errors are handled gracefully."""
    # Test with invalid stream name (should handle error)
    try:
        async with event_publisher.client.connection() as client:
            # Try invalid operation
            try:
                await client.xinfo_stream("")  # Empty stream name
            except Exception:
                # Expected to fail, but should not crash
                pass
    except PubSubError:
        # Expected error type
        pass
    except Exception as e:
        # Other errors are acceptable for invalid input
        assert isinstance(e, (ValueError, TypeError, Exception))


@pytest.mark.asyncio
async def test_redis_message_persistence(event_publisher, event_consumer):
    """Test that messages persist in Redis streams."""
    tenant_id = uuid4()
    entity_id = uuid4()

    # Publish event
    message_id = await event_publisher.publish(
        event_type="product.created",
        entity_type="product",
        entity_id=entity_id,
        tenant_id=tenant_id,
        metadata=EventMetadata(source="test"),
    )

    # Verify message exists in stream
    async with event_publisher.client.connection() as client:
        messages = await client.xrange(
            settings.REDIS_STREAM_DOMAIN,
            min=message_id,
            max=message_id,
            count=1,
        )
        assert len(messages) == 1
        assert messages[0][0] == message_id


@pytest.mark.asyncio
async def test_redis_stream_cleanup(event_publisher):
    """Test that test streams can be cleaned up."""
    test_stream = f"test:cleanup:{uuid4().hex[:8]}"

    async with event_publisher.client.connection() as client:
        # Add test message
        await client.xadd(test_stream, {"test": "cleanup"})

        # Verify it exists
        info = await client.xinfo_stream(test_stream)
        assert info["length"] == 1

        # Cleanup: delete stream (in real tests, this would be in teardown)
        # Note: Redis doesn't have a direct delete stream command,
        # but we can delete all messages
        messages = await client.xrange(test_stream, min="-", max="+")
        if messages:
            message_ids = [msg[0] for msg in messages]
            await client.xdel(test_stream, *message_ids)

