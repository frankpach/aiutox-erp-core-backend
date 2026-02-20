"""Unit tests for NotificationEventConsumer."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.notifications.consumer import NotificationEventConsumer
from app.core.pubsub import EventConsumer
from app.core.pubsub.models import Event, EventMetadata


@pytest.fixture
def mock_event_consumer():
    """Create a mock EventConsumer."""
    consumer = MagicMock(spec=EventConsumer)
    consumer.subscribe = AsyncMock()
    return consumer


@pytest.fixture
def notification_consumer(db_session, mock_event_consumer):
    """Create NotificationEventConsumer with mock consumer."""
    return NotificationEventConsumer(db_session, consumer=mock_event_consumer)


@pytest.mark.asyncio
async def test_consumer_initialization(notification_consumer):
    """Test NotificationEventConsumer initialization."""
    assert notification_consumer.db is not None
    assert notification_consumer.notification_service is not None
    assert notification_consumer._running is False


@pytest.mark.asyncio
async def test_start_subscribes_to_events(notification_consumer, mock_event_consumer):
    """Test that start() subscribes to events."""
    await notification_consumer.start()

    assert notification_consumer._running is True
    mock_event_consumer.subscribe.assert_called_once()
    call_args = mock_event_consumer.subscribe.call_args
    assert call_args[1]["group_name"] == "notifications-service"
    assert call_args[1]["consumer_name"] == "notifications-consumer-1"


@pytest.mark.asyncio
async def test_handle_event_sends_notification(
    notification_consumer, test_user, test_tenant
):
    """Test that handle_event sends notification."""
    # Create a test event
    event = Event(
        event_type="product.created",
        entity_type="product",
        entity_id=uuid4(),
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        metadata=EventMetadata(
            source="test",
            version="1.0",
            additional_data={"product_name": "Test Product", "sku": "TEST-001"},
        ),
    )

    # Mock notification service
    with patch.object(
        notification_consumer.notification_service, "send", new_callable=AsyncMock
    ) as mock_send:
        await notification_consumer._handle_event(event)

        # Verify send was called
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[1]["event_type"] == "product.created"
        assert call_args[1]["recipient_id"] == test_user.id
        assert (
            "email" in call_args[1]["channels"] or "in-app" in call_args[1]["channels"]
        )


@pytest.mark.asyncio
async def test_handle_event_skips_notification_events(notification_consumer):
    """Test that handle_event skips notification.* events."""
    event = Event(
        event_type="notification.sent",
        entity_type="notification",
        entity_id=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        metadata=EventMetadata(source="test", version="1.0"),
    )

    with patch.object(
        notification_consumer.notification_service, "send", new_callable=AsyncMock
    ) as mock_send:
        await notification_consumer._handle_event(event)

        # Should not send notification for notification events
        mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_extract_notification_data(notification_consumer):
    """Test extraction of notification data from event."""
    event = Event(
        event_type="product.created",
        entity_type="product",
        entity_id=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        metadata=EventMetadata(
            source="test",
            version="1.0",
            additional_data={"product_name": "Test Product", "sku": "TEST-001"},
        ),
    )

    data = notification_consumer._extract_notification_data(event)

    assert data["event_type"] == "product.created"
    assert data["entity_type"] == "product"
    assert data["product_name"] == "Test Product"
    assert data["sku"] == "TEST-001"
