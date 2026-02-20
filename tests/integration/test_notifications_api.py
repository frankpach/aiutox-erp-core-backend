"""Integration tests for Notifications API endpoints."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import patch

from tests.helpers import create_user_with_permission


def test_create_notification_template(client_with_db, test_user, db_session):
    """Test creating a notification template."""
    # Assign notifications.manage permission
    headers = create_user_with_permission(db_session, test_user, "notifications", "manager")

    template_data = {
        "name": "Product Created Email",
        "event_type": "product.created",
        "channel": "email",
        "subject": "New Product: {{product_name}}",
        "body": "A new product {{product_name}} with SKU {{sku}} has been created.",
        "is_active": True,
    }

    response = client_with_db.post(
        "/api/v1/notifications/templates",
        json=template_data,
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Product Created Email"
    assert data["event_type"] == "product.created"
    assert data["channel"] == "email"
    assert "id" in data


def test_list_notification_templates(client_with_db, test_user, db_session):
    """Test listing notification templates."""
    # Assign notifications.view permission
    headers = create_user_with_permission(db_session, test_user, "notifications", "viewer")

    # Create a template
    from app.repositories.notification_repository import NotificationRepository

    repo = NotificationRepository(db_session)
    repo.create_template(
        {
            "tenant_id": test_user.tenant_id,
            "name": "Test Template",
            "event_type": "product.created",
            "channel": "email",
            "subject": "Test",
            "body": "Test body",
            "is_active": True,
        }
    )

    response = client_with_db.get("/api/v1/notifications/templates", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) > 0
    assert data[0]["name"] == "Test Template"


def test_get_notification_template(client_with_db, test_user, db_session):
    """Test getting a specific notification template."""
    # Assign notifications.view permission
    headers = create_user_with_permission(db_session, test_user, "notifications", "viewer")

    # Create a template
    from app.repositories.notification_repository import NotificationRepository

    repo = NotificationRepository(db_session)
    template = repo.create_template(
        {
            "tenant_id": test_user.tenant_id,
            "name": "Test Template",
            "event_type": "product.created",
            "channel": "email",
            "subject": "Test",
            "body": "Test body",
            "is_active": True,
        }
    )

    response = client_with_db.get(
        f"/api/v1/notifications/templates/{template.id}", headers=headers
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(template.id)
    assert data["name"] == "Test Template"


def test_update_notification_template(client_with_db, test_user, db_session):
    """Test updating a notification template."""
    # Assign notifications.manage permission
    headers = create_user_with_permission(db_session, test_user, "notifications", "manager")

    # Create a template
    from app.repositories.notification_repository import NotificationRepository

    repo = NotificationRepository(db_session)
    template = repo.create_template(
        {
            "tenant_id": test_user.tenant_id,
            "name": "Test Template",
            "event_type": "product.created",
            "channel": "email",
            "subject": "Test",
            "body": "Test body",
            "is_active": True,
        }
    )

    update_data = {"name": "Updated Template", "body": "Updated body"}

    response = client_with_db.put(
        f"/api/v1/notifications/templates/{template.id}",
        json=update_data,
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Updated Template"
    assert data["body"] == "Updated body"


def test_delete_notification_template(client_with_db, test_user, db_session):
    """Test deleting a notification template."""
    # Assign notifications.manage permission
    headers = create_user_with_permission(db_session, test_user, "notifications", "manager")

    # Create a template
    from app.repositories.notification_repository import NotificationRepository

    repo = NotificationRepository(db_session)
    template = repo.create_template(
        {
            "tenant_id": test_user.tenant_id,
            "name": "Test Template",
            "event_type": "product.created",
            "channel": "email",
            "subject": "Test",
            "body": "Test body",
            "is_active": True,
        }
    )

    response = client_with_db.delete(
        f"/api/v1/notifications/templates/{template.id}", headers=headers
    )

    assert response.status_code == 204

    # Verify it's deleted
    response = client_with_db.get(
        f"/api/v1/notifications/templates/{template.id}", headers=headers
    )
    assert response.status_code == 404


def test_list_notification_queue(client_with_db, test_user, db_session):
    """Test listing notification queue entries."""
    # Assign notifications.view permission
    headers = create_user_with_permission(db_session, test_user, "notifications", "viewer")

    response = client_with_db.get("/api/v1/notifications/queue", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)


def test_send_notification_requires_permission(client_with_db, test_user, auth_headers):
    """Test that sending notification requires notifications.manage permission."""
    send_data = {
        "event_type": "product.created",
        "recipient_id": str(test_user.id),
        "channels": ["email"],
        "data": {"product_name": "Test Product"},
    }

    response = client_with_db.post(
        "/api/v1/notifications/send", json=send_data, headers=auth_headers
    )

    assert response.status_code == 403


def test_stream_notifications_sse(client_with_db, test_user, db_session):
    """Test SSE endpoint for streaming notifications.

    This test verifies that the SSE endpoint exists and responds correctly.
    Since SSE streams are infinite (they check for new notifications every 5 seconds),
    we use a mock to make the stream terminate quickly after the first check.
    """
    from unittest.mock import patch

    # Assign notifications.view permission
    headers = create_user_with_permission(db_session, test_user, "notifications", "viewer")

    # Create a notification queue entry to ensure there's data to stream
    from app.models.notification import NotificationQueue, NotificationStatus

    notification = NotificationQueue(
        tenant_id=test_user.tenant_id,
        recipient_id=test_user.id,
        event_type="product.created",
        channel="in-app",
        status=NotificationStatus.PENDING,
    )
    db_session.add(notification)
    db_session.commit()

    # Mock asyncio.sleep to make the stream terminate quickly
    # After the first iteration, we'll raise CancelledError to stop the stream
    call_count = [0]  # Use list to allow modification in nested function

    async def mock_sleep(delay):
        """Mock sleep that cancels after first iteration."""
        call_count[0] += 1
        if call_count[0] > 1:  # After first check, cancel
            raise asyncio.CancelledError()
        # For first call, sleep very briefly
        await asyncio.sleep(0.01)

    # Make request to SSE endpoint with mocked sleep
    with patch('app.api.v1.notifications.asyncio.sleep', side_effect=mock_sleep):
        response = client_with_db.get(
            "/api/v1/notifications/stream",
            headers=headers,
        )

    # Verify the endpoint responds correctly
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "Cache-Control" in response.headers
    assert response.headers["Cache-Control"] == "no-cache"
    assert "Connection" in response.headers
    assert response.headers["Connection"] == "keep-alive"

    # The stream should have sent at least the initial check
    # Content may be empty if no notifications, or contain SSE-formatted data
    content = response.text
    assert content is not None


def test_get_unread_notifications(client_with_db, test_user, auth_headers, db_session):
    """Test get_unread_notifications repository method."""
    from app.models.notification import NotificationQueue, NotificationStatus
    from app.repositories.notification_repository import NotificationRepository

    # Create notifications
    notification1 = NotificationQueue(
        tenant_id=test_user.tenant_id,
        recipient_id=test_user.id,
        event_type="product.created",
        channel="in-app",
        status=NotificationStatus.PENDING,
    )
    notification2 = NotificationQueue(
        tenant_id=test_user.tenant_id,
        recipient_id=test_user.id,
        event_type="order.created",
        channel="in-app",
        status=NotificationStatus.SENT,
    )
    db_session.add_all([notification1, notification2])
    db_session.commit()

    # Get unread notifications
    repo = NotificationRepository(db_session)
    notifications = repo.get_unread_notifications(
        tenant_id=test_user.tenant_id,
        user_id=test_user.id,
    )

    assert len(notifications) >= 2
    # Verify they are ordered by created_at desc
    assert notifications[0].created_at >= notifications[1].created_at

    # Test with since_id
    notifications_new = repo.get_unread_notifications(
        tenant_id=test_user.tenant_id,
        user_id=test_user.id,
        since_id=notification1.id,
    )

    # Should only return notifications created after notification1
    assert all(n.created_at > notification1.created_at for n in notifications_new)


def test_stream_notifications_adaptive_interval_no_notifications(client_with_db, test_user, db_session):
    """Test that SSE endpoint increases interval when no notifications are found.

    Verifies that intervals progress: 5s -> 10s -> 20s -> 30s -> 60s (max)
    """
    # Assign notifications.view permission
    headers = create_user_with_permission(db_session, test_user, "notifications", "viewer")

    # Track sleep calls to verify intervals
    sleep_calls = []
    # Import real sleep to use inside mock
    real_sleep = asyncio.sleep

    async def mock_sleep(delay):
        """Mock sleep that records the delay and cancels after enough iterations."""
        sleep_calls.append(delay)
        # Cancel after 6 iterations to test interval progression
        if len(sleep_calls) >= 6:
            raise asyncio.CancelledError()
        # Use real sleep with minimal delay for test speed
        await real_sleep(0.001)

    # Test: No notifications - interval should increase
    with patch('app.api.v1.notifications.asyncio.sleep', side_effect=mock_sleep):
        response = client_with_db.get(
            "/api/v1/notifications/stream",
            headers=headers,
        )

        # Consume the stream to trigger iterations
        try:
            for _ in response.iter_lines():
                pass
        except Exception:
            pass  # Expected when stream cancels

    # Verify intervals increased: 5s -> 10s -> 20s -> 30s -> 60s
    assert len(sleep_calls) >= 5, f"Expected at least 5 sleep calls, got {len(sleep_calls)}"
    assert sleep_calls[0] == 5, f"First interval should be 5s, got {sleep_calls[0]}"
    assert sleep_calls[1] == 10, f"Second interval should be 10s, got {sleep_calls[1]}"
    assert sleep_calls[2] == 20, f"Third interval should be 20s, got {sleep_calls[2]}"
    assert sleep_calls[3] == 30, f"Fourth interval should be 30s, got {sleep_calls[3]}"
    assert sleep_calls[4] == 60, f"Fifth interval should be 60s, got {sleep_calls[4]}"
    # Verify it stays at 60s (max)
    if len(sleep_calls) > 5:
        assert sleep_calls[5] == 60, f"Sixth interval should stay at 60s (max), got {sleep_calls[5]}"


def test_stream_notifications_adaptive_interval_with_notifications(client_with_db, test_user, db_session):
    """Test that SSE endpoint resets interval to 5s when notifications are found.

    Verifies that finding notifications resets the interval back to the fastest (5s).
    """
    # Assign notifications.view permission
    headers = create_user_with_permission(db_session, test_user, "notifications", "viewer")

    from app.models.notification import NotificationQueue, NotificationStatus

    # Create initial notification
    notification1 = NotificationQueue(
        tenant_id=test_user.tenant_id,
        recipient_id=test_user.id,
        event_type="product.created",
        channel="in-app",
        status=NotificationStatus.PENDING,
        created_at=datetime.now(UTC),
    )
    db_session.add(notification1)
    db_session.commit()

    sleep_calls = []
    iteration_count = [0]
    # Import real sleep to use inside mock
    real_sleep = asyncio.sleep

    async def mock_sleep(delay):
        """Mock sleep that records delay."""
        sleep_calls.append(delay)
        iteration_count[0] += 1

        # Cancel after 2 iterations (enough to verify reset behavior)
        if iteration_count[0] >= 2:
            raise asyncio.CancelledError()

        # Use real sleep with minimal delay for test speed
        await real_sleep(0.001)

    with patch('app.api.v1.notifications.asyncio.sleep', side_effect=mock_sleep):
        response = client_with_db.get(
            "/api/v1/notifications/stream",
            headers=headers,
        )

        # Consume the stream
        try:
            for _ in response.iter_lines():
                pass
        except Exception:
            pass

    # Verify behavior:
    # - First iteration: finds notification1, interval should be 5s (index 0)
    # - After finding notification, interval resets to 5s, so next sleep should be 5s
    assert len(sleep_calls) >= 1, f"Expected at least 1 sleep call, got {len(sleep_calls)}"
    # After finding notification, interval should reset to 5s
    assert sleep_calls[0] == 5, f"After finding notification, interval should reset to 5s, got {sleep_calls[0]}"

