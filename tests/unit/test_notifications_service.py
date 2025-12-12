"""Unit tests for NotificationService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.core.notifications.service import NotificationService
from app.models.notification import NotificationStatus, NotificationTemplate


@pytest.fixture
def notification_service(db_session):
    """Create NotificationService instance."""
    return NotificationService(db_session)


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
async def test_send_notification(notification_service, test_user, test_tenant, test_template):
    """Test sending a notification."""
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


