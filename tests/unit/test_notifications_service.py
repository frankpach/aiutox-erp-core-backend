"""Unit tests for NotificationService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.core.notifications.service import NotificationService
from app.core.pubsub import EventPublisher
from app.models.notification import NotificationStatus, NotificationTemplate


@pytest.fixture
def mock_event_publisher():
    """Create a mock EventPublisher."""
    publisher = MagicMock(spec=EventPublisher)
    publisher.publish = AsyncMock(return_value="message-id-123")
    return publisher


@pytest.fixture
def notification_service(db_session, mock_event_publisher):
    """Create NotificationService instance."""
    return NotificationService(db_session, event_publisher=mock_event_publisher)


@pytest.fixture
def test_template(db_session, test_tenant):
    """Create a test notification template."""
    from app.repositories.notification_repository import NotificationRepository

    repo = NotificationRepository(db_session)
    template = repo.create_template(
        {
            "tenant_id": test_tenant.id,
            "name": "Product Created Template",
            "event_type": "product.created",
            "channel": "email",
            "subject": "New Product: {{product_name}}",
            "body": "A new product {{product_name}} with SKU {{sku}} has been created.",
            "is_active": True,
        }
    )
    return template


@pytest.mark.asyncio
async def test_send_notification(
    notification_service, test_user, test_tenant, test_template, mock_event_publisher
):
    """Test sending a notification."""
    with patch("app.core.notifications.service.aiosmtplib") as mock_smtp:
        # Mock email sending
        mock_smtp.send = AsyncMock()

        result = await notification_service.send(
            event_type="product.created",
            recipient_id=test_user.id,
            channels=["email"],
            data={"product_name": "Test Product", "sku": "TEST-001"},
            tenant_id=test_tenant.id,
        )

        assert len(result) > 0
        assert result[0]["event_type"] == "product.created"
        assert result[0]["channel"] == "email"
        assert result[0]["status"] == "sent"

        # Verify event was published
        assert mock_event_publisher.publish.called
        call_args = mock_event_publisher.publish.call_args
        assert call_args[1]["event_type"] == "notification.sent"
        assert call_args[1]["entity_type"] == "notification"


@pytest.mark.asyncio
async def test_send_notification_respects_preferences(
    notification_service, test_user, test_tenant, test_template, db_session
):
    """Test that notifications respect user preferences."""
    from app.core.preferences.service import PreferencesService

    # Disable notifications for this event type
    prefs_service = PreferencesService(db_session)
    prefs_service.set_preference(
        user_id=test_user.id,
        tenant_id=test_tenant.id,
        preference_type="notification",
        key="product.created",
        value={"enabled": False},
    )

    result = await notification_service.send(
        event_type="product.created",
        recipient_id=test_user.id,
        channels=["email"],
        data={"product_name": "Test Product", "sku": "TEST-001"},
        tenant_id=test_tenant.id,
    )

    # Should return empty list because notifications are disabled
    assert len(result) == 0


@pytest.mark.asyncio
async def test_render_template(notification_service):
    """Test template rendering."""
    template_body = "Product {{product_name}} with SKU {{sku}}"
    data = {"product_name": "Test Product", "sku": "TEST-001"}

    rendered = notification_service._render_template(template_body, data)

    assert "Test Product" in rendered
    assert "TEST-001" in rendered
    assert "{{product_name}}" not in rendered
    assert "{{sku}}" not in rendered


@pytest.mark.asyncio
async def test_send_notification_publishes_failed_event(
    notification_service, test_user, test_tenant, test_template, mock_event_publisher, db_session
):
    """Test that failed notifications publish notification.failed event."""
    with patch("app.core.notifications.service.aiosmtplib") as mock_smtp:
        # Mock email sending to fail
        mock_smtp.send = AsyncMock(side_effect=Exception("SMTP Error"))

        result = await notification_service.send(
            event_type="product.created",
            recipient_id=test_user.id,
            channels=["email"],
            data={"product_name": "Test Product", "sku": "TEST-001"},
            tenant_id=test_tenant.id,
        )

        # Should still return result but with failed status
        assert len(result) > 0
        assert result[0]["status"] == "failed"

        # Verify failed event was published
        publish_calls = [call for call in mock_event_publisher.publish.call_args_list]
        failed_calls = [
            call
            for call in publish_calls
            if call[1].get("event_type") == "notification.failed"
        ]
        assert len(failed_calls) > 0


