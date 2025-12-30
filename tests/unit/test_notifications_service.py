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
    notification_service, test_user, test_tenant, test_template, mock_event_publisher, db_session
):
    """Test sending a notification."""
    from app.core.preferences.service import PreferencesService

    # Configure user preferences to allow email channel
    prefs_service = PreferencesService(db_session)
    prefs_service.set_preference(
        user_id=test_user.id,
        tenant_id=test_tenant.id,
        preference_type="notification",
        key="product.created",
        value={"enabled": True, "channels": ["email", "in-app"]},
    )

    # Mock SMTP settings to enable email sending
    mock_settings = MagicMock()
    mock_settings.SMTP_HOST = "smtp.test.com"
    mock_settings.SMTP_PORT = 587
    mock_settings.SMTP_USER = "test@test.com"
    mock_settings.SMTP_PASSWORD = "password"
    mock_settings.SMTP_FROM = "noreply@test.com"

    with patch("app.core.config_file.get_settings", return_value=mock_settings):
        import aiosmtplib
        with patch.object(aiosmtplib, "send", new_callable=AsyncMock) as mock_send:
            # Mock email sending
            mock_send.return_value = None

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
    from app.core.preferences.service import PreferencesService

    # Configure user preferences to allow email channel
    prefs_service = PreferencesService(db_session)
    prefs_service.set_preference(
        user_id=test_user.id,
        tenant_id=test_tenant.id,
        preference_type="notification",
        key="product.created",
        value={"enabled": True, "channels": ["email", "in-app"]},
    )

    # Mock SMTP settings to enable email sending
    mock_settings = MagicMock()
    mock_settings.SMTP_HOST = "smtp.test.com"
    mock_settings.SMTP_PORT = 587
    mock_settings.SMTP_USER = "test@test.com"
    mock_settings.SMTP_PASSWORD = "password"
    mock_settings.SMTP_FROM = "noreply@test.com"

    with patch("app.core.config_file.get_settings", return_value=mock_settings):
        import aiosmtplib
        with patch.object(aiosmtplib, "send", new_callable=AsyncMock) as mock_send:
            # Mock email sending to fail
            mock_send.side_effect = Exception("SMTP Error")

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


@pytest.mark.asyncio
async def test_send_sms(notification_service, test_user, test_tenant, db_session):
    """Test sending SMS notification."""
    from app.core.config.service import ConfigService
    from app.repositories.contact_method_repository import ContactMethodRepository
    from app.models.contact_method import ContactMethodType

    # Create phone contact method for user
    from app.models.contact_method import EntityType

    contact_repo = ContactMethodRepository(db_session)
    contact_repo.create(
        {
            "entity_type": EntityType.USER,
            "entity_id": test_user.id,
            "method_type": ContactMethodType.MOBILE,
            "value": "+1987654321",
            "is_primary": True,
        }
    )

    # Set SMS configuration
    config_service = ConfigService(db_session, use_cache=False)
    config_service.set(
        tenant_id=test_tenant.id,
        module="notifications",
        key="channels.sms.enabled",
        value=True,
    )
    config_service.set(
        tenant_id=test_tenant.id,
        module="notifications",
        key="channels.sms.provider",
        value="twilio",
    )
    config_service.set(
        tenant_id=test_tenant.id,
        module="notifications",
        key="channels.sms.account_sid",
        value="test_account_sid",
    )
    config_service.set(
        tenant_id=test_tenant.id,
        module="notifications",
        key="channels.sms.auth_token",
        value="test_auth_token",
    )
    config_service.set(
        tenant_id=test_tenant.id,
        module="notifications",
        key="channels.sms.from_number",
        value="+1234567890",
    )

    import httpx
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"sid": "SM1234567890"}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        await notification_service._send_sms(test_user.id, "Test SMS message")

        # Verify HTTP request was made
        assert mock_client.post.called
        call_args = mock_client.post.call_args
        assert "https://api.twilio.com" in call_args[0][0]


@pytest.mark.asyncio
async def test_send_sms_no_phone(notification_service, test_user, test_tenant, db_session):
    """Test sending SMS when user has no phone number."""
    from app.core.config.service import ConfigService

    # Set SMS configuration (but user has no phone)
    config_service = ConfigService(db_session, use_cache=False)
    config_service.set(
        tenant_id=test_tenant.id,
        module="notifications",
        key="channels.sms.enabled",
        value=True,
    )

    with pytest.raises(ValueError, match="phone"):
        await notification_service._send_sms(test_user.id, "Test SMS message")


@pytest.mark.asyncio
async def test_send_webhook(notification_service):
    """Test sending webhook notification."""
    import httpx
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        payload = {"body": "Test webhook message", "event_type": "test.event"}
        await notification_service._send_webhook("https://webhook.example.com/test", payload)

        # Verify HTTP request was made
        assert mock_client.post.called
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://webhook.example.com/test"
        assert call_args[1]["json"] == payload


@pytest.mark.asyncio
async def test_send_webhook_no_url(notification_service):
    """Test sending webhook without URL raises error."""
    with pytest.raises(ValueError, match="URL is required"):
        await notification_service._send_webhook(None, {"body": "Test"})


@pytest.mark.asyncio
async def test_send_webhook_timeout(notification_service):
    """Test webhook timeout handling."""
    import httpx
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client_class.return_value = mock_client

        payload = {"body": "Test webhook message"}
        with pytest.raises(Exception, match="timeout"):
            await notification_service._send_webhook("https://webhook.example.com/test", payload)


