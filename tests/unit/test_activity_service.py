"""Unit tests for ActivityService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.core.activities.service import ActivityService
from app.core.pubsub import EventPublisher
from app.models.activity import Activity, ActivityType


@pytest.fixture
def mock_event_publisher():
    """Create a mock EventPublisher."""
    publisher = MagicMock(spec=EventPublisher)
    publisher.publish = AsyncMock(return_value="message-id-123")
    return publisher


@pytest.fixture
def activity_service(db_session, mock_event_publisher):
    """Create ActivityService instance."""
    return ActivityService(db_session, event_publisher=mock_event_publisher)


def test_create_activity(activity_service, test_user, test_tenant, mock_event_publisher):
    """Test creating an activity."""
    entity_id = uuid4()
    activity = activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type=ActivityType.COMMENT,
        title="Test Comment",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        description="This is a test comment",
        metadata={"priority": "high"},
    )

    assert activity.id is not None
    assert activity.entity_type == "product"
    assert activity.entity_id == entity_id
    assert activity.activity_type == ActivityType.COMMENT
    assert activity.title == "Test Comment"
    assert activity.description == "This is a test comment"
    assert activity.user_id == test_user.id
    assert activity.tenant_id == test_tenant.id
    # Note: metadata is stored in activity_metadata column but accessed via metadata attribute
    # The model uses activity_metadata as column name but exposes it as metadata
    # The model uses activity_metadata as the attribute name
    assert activity.activity_metadata == {"priority": "high"}

    # Verify event was published
    assert mock_event_publisher.publish.called


def test_get_activities(activity_service, test_user, test_tenant):
    """Test getting activities for an entity."""
    entity_id = uuid4()

    # Create multiple activities
    activity1 = activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type=ActivityType.COMMENT,
        title="Comment 1",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    activity2 = activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type=ActivityType.STATUS_CHANGE,
        title="Status Changed",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    # Get all activities
    activities = activity_service.get_activities(
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
    )

    assert len(activities) == 2
    assert activities[0].id == activity2.id  # Most recent first
    assert activities[1].id == activity1.id

    # Filter by activity type
    comments = activity_service.get_activities(
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
        activity_type=ActivityType.COMMENT,
    )

    assert len(comments) == 1
    assert comments[0].id == activity1.id


def test_count_activities(activity_service, test_user, test_tenant):
    """Test counting activities."""
    entity_id = uuid4()

    # Create activities
    activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type=ActivityType.COMMENT,
        title="Comment 1",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type=ActivityType.COMMENT,
        title="Comment 2",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type=ActivityType.STATUS_CHANGE,
        title="Status Changed",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    # Count all activities
    total = activity_service.count_activities(
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
    )
    assert total == 3

    # Count by type
    comment_count = activity_service.count_activities(
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
        activity_type=ActivityType.COMMENT,
    )
    assert comment_count == 2


def test_update_activity(activity_service, test_user, test_tenant, mock_event_publisher):
    """Test updating an activity."""
    entity_id = uuid4()
    activity = activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type=ActivityType.COMMENT,
        title="Original Title",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        description="Original description",
    )

    # Update activity
    updated = activity_service.update_activity(
        activity_id=activity.id,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        title="Updated Title",
        description="Updated description",
        metadata={"updated": True},
    )

    assert updated is not None
    assert updated.title == "Updated Title"
    assert updated.description == "Updated description"
    # The model uses activity_metadata as the attribute name
    assert updated.activity_metadata == {"updated": True}

    # Verify event was published
    publish_calls = [call for call in mock_event_publisher.publish.call_args_list]
    updated_calls = [
        call for call in publish_calls if call[1].get("event_type") == "activity.updated"
    ]
    assert len(updated_calls) > 0


def test_update_activity_not_found(activity_service, test_user, test_tenant):
    """Test updating a non-existent activity."""
    fake_id = uuid4()
    updated = activity_service.update_activity(
        activity_id=fake_id,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        title="Updated Title",
    )

    assert updated is None


def test_delete_activity(activity_service, test_user, test_tenant, mock_event_publisher):
    """Test deleting an activity."""
    entity_id = uuid4()
    activity = activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type=ActivityType.COMMENT,
        title="To Delete",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    # Delete activity
    deleted = activity_service.delete_activity(
        activity_id=activity.id,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    assert deleted is True

    # Verify it's gone
    activities = activity_service.get_activities(
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
    )
    assert len(activities) == 0

    # Verify event was published
    publish_calls = [call for call in mock_event_publisher.publish.call_args_list]
    deleted_calls = [
        call for call in publish_calls if call[1].get("event_type") == "activity.deleted"
    ]
    assert len(deleted_calls) > 0


def test_delete_activity_not_found(activity_service, test_user, test_tenant):
    """Test deleting a non-existent activity."""
    fake_id = uuid4()
    deleted = activity_service.delete_activity(
        activity_id=fake_id,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    assert deleted is False


def test_search_activities(activity_service, test_user, test_tenant):
    """Test searching activities."""
    entity_id = uuid4()

    # Create activities with different titles
    activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type=ActivityType.COMMENT,
        title="Product Review",
        description="This product is great",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type=ActivityType.COMMENT,
        title="Price Update",
        description="Updated the price",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    # Search by title
    results = activity_service.search_activities(
        tenant_id=test_tenant.id,
        query="Review",
        entity_type="product",
    )

    assert len(results) == 1
    assert "Review" in results[0].title

    # Search by description
    results = activity_service.search_activities(
        tenant_id=test_tenant.id,
        query="price",
        entity_type="product",
    )

    assert len(results) == 1
    assert "price" in results[0].description.lower() or "price" in results[0].title.lower()


def test_count_all_activities(activity_service, test_user, test_tenant):
    """Test counting all activities for a tenant."""
    entity_id1 = uuid4()
    entity_id2 = uuid4()

    # Create activities for different entities
    activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id1,
        activity_type=ActivityType.COMMENT,
        title="Comment 1",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id2,
        activity_type=ActivityType.COMMENT,
        title="Comment 2",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    activity_service.create_activity(
        entity_type="order",
        entity_id=uuid4(),
        activity_type=ActivityType.STATUS_CHANGE,
        title="Order Status",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    # Count all
    total = activity_service.count_all_activities(tenant_id=test_tenant.id)
    assert total == 3

    # Count by type
    comment_count = activity_service.count_all_activities(
        tenant_id=test_tenant.id, activity_type=ActivityType.COMMENT
    )
    assert comment_count == 2


def test_count_search_activities(activity_service, test_user, test_tenant):
    """Test counting search results."""
    entity_id = uuid4()

    activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type=ActivityType.COMMENT,
        title="Test Activity",
        description="This is a test",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    activity_service.create_activity(
        entity_type="product",
        entity_id=entity_id,
        activity_type=ActivityType.COMMENT,
        title="Another Activity",
        description="Another test",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    # Count search results
    count = activity_service.count_search_activities(
        tenant_id=test_tenant.id,
        query_text="test",
        entity_type="product",
    )

    assert count == 2

