"""Unit tests for ActivityService."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.activities.service import ActivityService
from app.core.pubsub import EventPublisher


@pytest.fixture
def mock_event_publisher():
    """Create a mock EventPublisher."""
    publisher = MagicMock(spec=EventPublisher)
    publisher.publish = AsyncMock(return_value="message-id-123")
    return publisher


@pytest.fixture
def activity_service(db_session, mock_event_publisher):
    """Create ActivityService instance."""
    return ActivityService(db=db_session, event_publisher=mock_event_publisher)


def test_create_activity(
    activity_service, test_user, test_tenant, mock_event_publisher
):
    """Test creating an activity."""
    entity_id = uuid4()
    activity = activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type="comment",
        title="Test Comment",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        description="This is a test comment",
    )

    assert activity.entity_type == "product"
    assert activity.entity_id == entity_id
    assert activity.activity_type == "comment"
    assert activity.title == "Test Comment"
    assert activity.description == "This is a test comment"
    assert activity.tenant_id == test_tenant.id
    assert activity.user_id == test_user.id

    # Verify event was published
    assert mock_event_publisher.publish.called


def test_get_activities(activity_service, test_user, test_tenant):
    """Test getting activities for an entity."""
    entity_id = uuid4()

    # Create multiple activities
    activity1 = activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type="comment",
        title="Comment 1",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )
    activity2 = activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type="call",
        title="Call 1",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    # Get all activities for entity
    activities = activity_service.get_activities(
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
    )

    assert len(activities) >= 2
    assert any(a.id == activity1.id for a in activities)
    assert any(a.id == activity2.id for a in activities)

    # Filter by activity type
    comments = activity_service.get_activities(
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
        activity_type="comment",
    )

    assert any(a.id == activity1.id for a in comments)
    assert not any(a.id == activity2.id for a in comments)


def test_search_activities(activity_service, test_user, test_tenant):
    """Test searching activities."""
    entity_id = uuid4()

    # Create activities with different titles
    activity1 = activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type="comment",
        title="Important Update",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        description="This is important",
    )
    activity2 = activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type="note",
        title="Regular Note",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )
    assert activity2.title == "Regular Note"

    # Search for "Important"
    results = activity_service.search_activities(
        tenant_id=test_tenant.id,
        query="Important",
    )

    assert len(results) >= 1
    assert any(a.id == activity1.id for a in results)
    # activity2 might or might not be in results depending on search implementation


def test_update_activity(activity_service, test_user, test_tenant):
    """Test updating an activity."""
    entity_id = uuid4()

    # Create an activity
    activity = activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type="comment",
        title="Original Title",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    # Update it
    updated = activity_service.update_activity(
        activity.id,
        test_tenant.id,
        test_user.id,
        title="Updated Title",
        description="Updated description",
    )

    assert updated is not None
    assert updated.title == "Updated Title"
    assert updated.description == "Updated description"


def test_delete_activity(activity_service, test_user, test_tenant):
    """Test deleting an activity."""
    entity_id = uuid4()

    # Create an activity
    activity = activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type="comment",
        title="Test Comment",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    # Delete it
    deleted = activity_service.delete_activity(
        activity.id, test_tenant.id, test_user.id
    )

    assert deleted is True

    # Verify it's deleted
    activities = activity_service.get_activities(
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
    )
    assert not any(a.id == activity.id for a in activities)
