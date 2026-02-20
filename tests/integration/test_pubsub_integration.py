"""Integration tests for Pub-Sub module with real Redis."""

import asyncio
from uuid import uuid4

import pytest

from app.core.config_file import get_settings
from app.core.pubsub.client import RedisStreamsClient
from app.core.pubsub.consumer import EventConsumer
from app.core.pubsub.models import Event, EventMetadata
from app.core.pubsub.publisher import EventPublisher

settings = get_settings()

# Timeout para evitar que los tests se cuelguen
TEST_TIMEOUT = 10.0  # 10 segundos máximo por test

# Skip all tests in this module if Redis is not available
pytestmark = pytest.mark.redis


@pytest.fixture
async def redis_client():
    """Create Redis client for testing."""
    # Convert Docker hostname to localhost for tests (when running outside Docker)
    redis_url = settings.REDIS_URL
    if "redis:" in redis_url or "@redis:" in redis_url:
        redis_url = redis_url.replace("@redis:6379", "@localhost:6379")
        redis_url = redis_url.replace("redis:6379", "localhost:6379")

    client = RedisStreamsClient(redis_url=redis_url, password=settings.REDIS_PASSWORD)
    yield client
    await client.close()


@pytest.fixture
def event_publisher(redis_client):
    """Create EventPublisher for testing."""
    return EventPublisher(client=redis_client)


@pytest.fixture
def event_consumer(redis_client):
    """Create EventConsumer for testing."""
    return EventConsumer(client=redis_client)


@pytest.fixture(autouse=True)
async def clean_redis_streams(redis_client):
    """Clean Redis streams and consumer groups before each test to avoid reading old messages."""
    async with redis_client.connection() as client:
        from app.core.config_file import get_settings

        settings = get_settings()

        streams_to_clean = [
            settings.REDIS_STREAM_DOMAIN,
            settings.REDIS_STREAM_TECHNICAL,
        ]

        for stream_name in streams_to_clean:
            try:
                # Delete all consumer groups for this stream (so they can be recreated with start_id="$")
                try:
                    groups_info = await client.xinfo_groups(stream_name)
                    for group in groups_info:
                        group_name = (
                            group.get("name") or group.get(b"name", b"").decode()
                        )
                        if group_name and group_name.startswith("test-"):
                            try:
                                await client.xgroup_destroy(stream_name, group_name)
                            except Exception:
                                pass  # Group might not exist
                except Exception:
                    pass  # Stream might not exist or have no groups

                # Get all message IDs in the stream and delete them
                messages = await client.xrange(
                    stream_name, min="-", max="+", count=10000
                )
                if messages:
                    message_ids = [msg_id for msg_id, _ in messages]
                    if message_ids:
                        await client.xdel(stream_name, *message_ids)
            except Exception:
                # Stream might not exist, which is fine
                pass

    yield


@pytest.mark.asyncio
@pytest.mark.integration
async def test_publish_and_consume_event(
    redis_client, event_publisher, event_consumer, redis_available
):
    """Test publishing and consuming an event with timeout."""
    if not redis_available:
        pytest.skip("Redis is not available")
    tenant_id = uuid4()
    entity_id = uuid4()
    user_id = uuid4()

    received_events = []
    event_received = asyncio.Event()

    async def callback(event: Event):
        # Solo procesar el evento que estamos buscando
        if event.entity_id == entity_id and event.tenant_id == tenant_id:
            received_events.append(event)
            event_received.set()  # Señalizar que recibimos el evento

    async def test_workflow():
        # Clean up any existing test data
        stream_name = settings.REDIS_STREAM_DOMAIN
        async with redis_client.connection() as client:
            # Delete stream if exists to start fresh
            try:
                await client.delete(stream_name)
            except Exception:
                pass  # Stream may not exist

        # Subscribe to events (use start_id="$" to only read new messages)
        await event_consumer.subscribe(
            group_name="test-group",
            consumer_name="test-consumer",
            event_types=["product.created"],
            callback=callback,
            start_id="$",  # Only read new messages (after this point)
            recreate_group=True,  # Recreate group to ensure correct start_id
        )

        # Wait a bit for subscription to be ready
        await asyncio.sleep(0.2)

        # Publish event
        message_id = await event_publisher.publish(
            event_type="product.created",
            entity_type="product",
            entity_id=entity_id,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=EventMetadata(source="test_service"),
        )

        assert message_id is not None

        # Wait for event to be received (con timeout)
        try:
            await asyncio.wait_for(event_received.wait(), timeout=3.0)
        except TimeoutError:
            pytest.fail("Event was not received within timeout")

        # Stop consumer inmediatamente
        await event_consumer.stop()

        # Verificar que el evento fue recibido
        assert len(received_events) >= 1
        event = received_events[0]
        assert event.event_type == "product.created"
        assert event.entity_id == entity_id
        assert event.tenant_id == tenant_id
        assert event.user_id == user_id

    # Ejecutar con timeout global
    await asyncio.wait_for(test_workflow(), timeout=TEST_TIMEOUT)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_stream_selection_domain_vs_technical(event_publisher, redis_available):
    """Test that events are published to correct streams."""
    if not redis_available:
        pytest.skip("Redis is not available")
    tenant_id = uuid4()
    entity_id = uuid4()

    async def test_workflow():
        # Domain event
        domain_message_id = await event_publisher.publish(
            event_type="product.created",
            entity_type="product",
            entity_id=entity_id,
            tenant_id=tenant_id,
        )

        # Technical event
        technical_message_id = await event_publisher.publish(
            event_type="system.error",
            entity_type="system",
            entity_id=entity_id,
            tenant_id=tenant_id,
        )

        assert domain_message_id is not None
        assert technical_message_id is not None

        # Verify streams exist and have messages
        async with event_publisher.client.connection() as client:
            domain_info = await client.xinfo_stream(settings.REDIS_STREAM_DOMAIN)
            technical_info = await client.xinfo_stream(settings.REDIS_STREAM_TECHNICAL)

            assert domain_info["length"] >= 1
            assert technical_info["length"] >= 1

    await asyncio.wait_for(test_workflow(), timeout=TEST_TIMEOUT)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_consumer_group_creation(redis_client, redis_available):
    """Test consumer group creation."""
    if not redis_available:
        pytest.skip("Redis is not available")
    stream_name = "test:stream"
    group_name = f"test-group-{uuid4().hex[:8]}"  # Unique group name

    async def test_workflow():
        # Clean up stream if exists
        async with redis_client.connection() as client:
            try:
                await client.delete(stream_name)
            except Exception:
                pass  # Stream may not exist

        # Create group (will create stream if it doesn't exist)
        created = await redis_client.create_group(stream_name, group_name)
        assert created is True, f"Expected True, got {created}"

        # Try to create again (should return False)
        created_again = await redis_client.create_group(stream_name, group_name)
        assert created_again is False, f"Expected False, got {created_again}"

        # Verify group exists
        group_info = await redis_client.get_group_info(stream_name, group_name)
        assert group_info["name"] == group_name

    await asyncio.wait_for(test_workflow(), timeout=TEST_TIMEOUT)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_event_metadata_preserved(
    event_publisher, event_consumer, redis_available
):
    """Test that event metadata is preserved through publish/consume."""
    if not redis_available:
        pytest.skip("Redis is not available")
    tenant_id = uuid4()
    entity_id = uuid4()

    original_metadata = EventMetadata(
        source="test_service",
        version="2.0",
        additional_data={"key": "value", "number": 42},
    )

    received_events = []
    event_received = asyncio.Event()

    async def callback(event: Event):
        received_events.append(event)
        event_received.set()

    async def test_workflow():
        await event_consumer.subscribe(
            group_name="test-group-2",
            consumer_name="test-consumer-2",
            event_types=["product.updated"],
            callback=callback,
            start_id="$",  # Only read new messages (after this point)
            recreate_group=True,  # Recreate group to ensure correct start_id
        )

        await asyncio.sleep(0.2)

        await event_publisher.publish(
            event_type="product.updated",
            entity_type="product",
            entity_id=entity_id,
            tenant_id=tenant_id,
            metadata=original_metadata,
        )

        # Wait for event with timeout
        try:
            await asyncio.wait_for(event_received.wait(), timeout=3.0)
        except TimeoutError:
            pytest.fail("Event was not received within timeout")

        await event_consumer.stop()

        assert len(received_events) >= 1
        event = received_events[0]
        assert event.metadata.source == original_metadata.source
        assert event.metadata.version == original_metadata.version
        assert event.metadata.additional_data == original_metadata.additional_data

    await asyncio.wait_for(test_workflow(), timeout=TEST_TIMEOUT)
