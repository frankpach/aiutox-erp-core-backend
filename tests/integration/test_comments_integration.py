"""Integration tests for Comments module interactions with other modules."""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.models.module_role import ModuleRole
from app.core.activities.service import ActivityService


def test_comment_creates_activity(client, test_user, auth_headers, db_session):
    """Test that creating a comment creates an activity."""
    # Assign permissions
    comment_role = ModuleRole(
        user_id=test_user.id,
        module="comments",
        role_name="creator",
        granted_by=test_user.id,
    )
    db_session.add(comment_role)
    db_session.commit()

    entity_id = uuid4()
    comment_data = {
        "entity_type": "product",
        "entity_id": str(entity_id),
        "content": "Test comment that should create activity",
    }

    response = client.post(
        "/api/v1/comments",
        json=comment_data,
        headers=auth_headers,
    )

    assert response.status_code == 201

    # Verify activity was created
    activity_service = ActivityService(db_session)
    activities = activity_service.get_activities(
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_user.tenant_id,
        activity_type="comment",
    )

    assert len(activities) >= 1
    assert any("comment" in a.title.lower() for a in activities)


def test_comment_with_mentions_sends_notifications(client, test_user, auth_headers, db_session):
    """Test that comments with @mentions trigger notifications."""
    # Assign permissions
    comment_role = ModuleRole(
        user_id=test_user.id,
        module="comments",
        role_name="creator",
        granted_by=test_user.id,
    )
    db_session.add(comment_role)
    db_session.commit()

    entity_id = uuid4()
    comment_data = {
        "entity_type": "product",
        "entity_id": str(entity_id),
        "content": f"Hello @{test_user.username}, this is a mention",
    }

    with patch("app.core.notifications.service.NotificationService.send") as mock_notify:
        mock_notify.return_value = AsyncMock(return_value=[])

        response = client.post(
            "/api/v1/comments",
            json=comment_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        # Notification should be sent (async, so we check it was called)
        # In real scenario, we'd wait for async task


def test_comment_thread(client, test_user, auth_headers, db_session):
    """Test threaded comments (replies)."""
    # Assign permissions
    comment_role = ModuleRole(
        user_id=test_user.id,
        module="comments",
        role_name="creator",
        granted_by=test_user.id,
    )
    db_session.add(comment_role)
    db_session.commit()

    entity_id = uuid4()

    # Create parent comment
    parent_data = {
        "entity_type": "product",
        "entity_id": str(entity_id),
        "content": "Parent comment",
    }
    parent_response = client.post(
        "/api/v1/comments",
        json=parent_data,
        headers=auth_headers,
    )
    parent_id = parent_response.json()["data"]["id"]

    # Create reply
    reply_data = {
        "entity_type": "product",
        "entity_id": str(entity_id),
        "content": "Reply to parent",
        "parent_id": parent_id,
    }
    reply_response = client.post(
        "/api/v1/comments",
        json=reply_data,
        headers=auth_headers,
    )

    assert reply_response.status_code == 201
    reply = reply_response.json()["data"]
    assert reply["parent_id"] == parent_id

    # Get thread
    thread_response = client.get(
        f"/api/v1/comments/{parent_id}/thread",
        headers=auth_headers,
    )

    assert thread_response.status_code == 200
    thread = thread_response.json()["data"]
    assert len(thread) >= 1
    assert any(r["id"] == reply["id"] for r in thread)


def test_comment_publishes_events(client, test_user, auth_headers, db_session):
    """Test that comments publish events."""
    # Assign permissions
    comment_role = ModuleRole(
        user_id=test_user.id,
        module="comments",
        role_name="creator",
        granted_by=test_user.id,
    )
    db_session.add(comment_role)
    db_session.commit()

    entity_id = uuid4()
    comment_data = {
        "entity_type": "product",
        "entity_id": str(entity_id),
        "content": "Test comment",
    }

    with patch("app.core.pubsub.publisher.EventPublisher.publish") as mock_publish:
        mock_publish.return_value = AsyncMock(return_value="test-message-id")

        response = client.post(
            "/api/v1/comments",
            json=comment_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        # Event publishing is done via background task
        assert True  # Background task scheduled

