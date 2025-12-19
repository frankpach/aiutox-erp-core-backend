"""Unit tests for CommentService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.core.comments.service import CommentService, MentionParser
from app.core.pubsub import EventPublisher


@pytest.fixture
def mock_event_publisher():
    """Create a mock EventPublisher."""
    publisher = MagicMock(spec=EventPublisher)
    publisher.publish = AsyncMock(return_value="message-id-123")
    return publisher


@pytest.fixture
def comment_service(db_session, mock_event_publisher):
    """Create CommentService instance."""
    return CommentService(db=db_session, event_publisher=mock_event_publisher)


def test_extract_mentions():
    """Test extracting mentions from content."""
    content = "Hello @john and @jane, how are you?"
    mentions = MentionParser.extract_mentions(content)

    assert "john" in mentions
    assert "jane" in mentions
    assert len(mentions) == 2


def test_create_comment(comment_service, test_user, test_tenant, mock_event_publisher):
    """Test creating a comment."""
    entity_id = uuid4()
    comment = comment_service.create_comment(
        comment_data={
            "entity_type": "product",
            "entity_id": entity_id,
            "content": "This is a test comment",
        },
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    assert comment.entity_type == "product"
    assert comment.entity_id == entity_id
    assert comment.content == "This is a test comment"
    assert comment.tenant_id == test_tenant.id
    assert comment.created_by == test_user.id

    # Verify event was published
    assert mock_event_publisher.publish.called


def test_get_comments_by_entity(comment_service, test_user, test_tenant):
    """Test getting comments for an entity."""
    entity_id = uuid4()

    # Create multiple comments
    comment1 = comment_service.create_comment(
        comment_data={
            "entity_type": "product",
            "entity_id": entity_id,
            "content": "Comment 1",
        },
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    comments = comment_service.get_comments_by_entity(
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
    )

    assert len(comments) >= 1
    assert any(c.id == comment1.id for c in comments)


def test_update_comment(comment_service, test_user, test_tenant):
    """Test updating a comment."""
    entity_id = uuid4()
    comment = comment_service.create_comment(
        comment_data={
            "entity_type": "product",
            "entity_id": entity_id,
            "content": "Original comment",
        },
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    updated_comment = comment_service.update_comment(
        comment_id=comment.id,
        tenant_id=test_tenant.id,
        comment_data={"content": "Updated comment"},
    )

    assert updated_comment is not None
    assert updated_comment.content == "Updated comment"
    assert updated_comment.is_edited == True








