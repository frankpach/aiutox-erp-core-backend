"""Unit tests for EventPublisher."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.config_file import get_settings
from app.core.pubsub.client import RedisStreamsClient
from app.core.pubsub.errors import PublishError
from app.core.pubsub.models import EventMetadata
from app.core.pubsub.publisher import EventPublisher

settings = get_settings()


@pytest.fixture
def mock_client():
    """Create a mock RedisStreamsClient."""
    return MagicMock(spec=RedisStreamsClient)


@pytest.fixture
def event_publisher(mock_client):
    """Create EventPublisher with mock client."""
    return EventPublisher(client=mock_client)


@pytest.mark.asyncio
async def test_publish_domain_event(event_publisher, mock_client):
    """Test publishing a domain event."""
    tenant_id = uuid4()
    entity_id = uuid4()
    user_id = uuid4()

    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock(return_value="1000-0")
    mock_client.connection.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
    mock_client.connection.return_value.__aexit__ = AsyncMock(return_value=False)

    message_id = await event_publisher.publish(
        event_type="product.created",
        entity_type="product",
        entity_id=entity_id,
        tenant_id=tenant_id,
        user_id=user_id,
        metadata=EventMetadata(source="test_service"),
    )

    assert message_id == "1000-0"
    mock_redis.xadd.assert_called_once()
    call_args = mock_redis.xadd.call_args
    assert call_args[0][0] == settings.REDIS_STREAM_DOMAIN
    assert call_args[0][1]["event_type"] == "product.created"


@pytest.mark.asyncio
async def test_publish_technical_event(event_publisher, mock_client):
    """Test publishing a technical event."""
    tenant_id = uuid4()
    entity_id = uuid4()

    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock(return_value="2000-0")
    mock_client.connection.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
    mock_client.connection.return_value.__aexit__ = AsyncMock(return_value=False)

    message_id = await event_publisher.publish(
        event_type="system.error",
        entity_type="system",
        entity_id=entity_id,
        tenant_id=tenant_id,
    )

    assert message_id == "2000-0"
    call_args = mock_redis.xadd.call_args
    assert call_args[0][0] == settings.REDIS_STREAM_TECHNICAL


@pytest.mark.asyncio
async def test_publish_without_user_id(event_publisher, mock_client):
    """Test publishing event without user_id."""
    tenant_id = uuid4()
    entity_id = uuid4()

    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock(return_value="1000-0")
    mock_client.connection.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
    mock_client.connection.return_value.__aexit__ = AsyncMock(return_value=False)

    message_id = await event_publisher.publish(
        event_type="product.created",
        entity_type="product",
        entity_id=entity_id,
        tenant_id=tenant_id,
    )

    assert message_id == "1000-0"
    call_args = mock_redis.xadd.call_args
    event_data = call_args[0][1]
    assert event_data["user_id"] == ""


@pytest.mark.asyncio
async def test_publish_with_custom_metadata(event_publisher, mock_client):
    """Test publishing event with custom metadata."""
    tenant_id = uuid4()
    entity_id = uuid4()
    metadata = EventMetadata(
        source="custom_service",
        version="2.0",
        additional_data={"key": "value", "number": 42},
    )

    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock(return_value="1000-0")
    mock_client.connection.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
    mock_client.connection.return_value.__aexit__ = AsyncMock(return_value=False)

    await event_publisher.publish(
        event_type="product.created",
        entity_type="product",
        entity_id=entity_id,
        tenant_id=tenant_id,
        metadata=metadata,
    )

    call_args = mock_redis.xadd.call_args
    event_data = call_args[0][1]
    assert event_data["metadata_source"] == "custom_service"
    assert event_data["metadata_version"] == "2.0"


@pytest.mark.asyncio
async def test_publish_invalid_event_type(event_publisher, mock_client):
    """Test publishing event with invalid event_type format."""
    tenant_id = uuid4()
    entity_id = uuid4()

    with pytest.raises(PublishError, match="Invalid event data"):
        await event_publisher.publish(
            event_type="InvalidFormat",  # Should be lowercase with dot
            entity_type="product",
            entity_id=entity_id,
            tenant_id=tenant_id,
        )


@pytest.mark.asyncio
async def test_publish_redis_error(event_publisher, mock_client):
    """Test publishing when Redis operation fails."""
    tenant_id = uuid4()
    entity_id = uuid4()

    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock(side_effect=Exception("Redis error"))
    mock_client.connection.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
    mock_client.connection.return_value.__aexit__ = AsyncMock(return_value=False)

    with pytest.raises(PublishError, match="Failed to publish event"):
        await event_publisher.publish(
            event_type="product.created",
            entity_type="product",
            entity_id=entity_id,
            tenant_id=tenant_id,
        )


@pytest.mark.asyncio
async def test_determine_stream_domain():
    """Test stream determination for domain events."""
    mock_client = MagicMock()
    publisher = EventPublisher(client=mock_client)

    domain_events = [
        "product.created",
        "inventory.stock_low",
        "customer.created",
        "order.completed",
    ]

    for event_type in domain_events:
        stream = publisher._determine_stream(event_type)
        assert stream == settings.REDIS_STREAM_DOMAIN


@pytest.mark.asyncio
async def test_determine_stream_technical():
    """Test stream determination for technical events."""
    mock_client = MagicMock()
    publisher = EventPublisher(client=mock_client)

    technical_events = [
        "system.error",
        "integration.failed",
        "audit.event",
        "notification.sent",
        "notification.failed",
    ]

    for event_type in technical_events:
        stream = publisher._determine_stream(event_type)
        assert stream == settings.REDIS_STREAM_TECHNICAL










