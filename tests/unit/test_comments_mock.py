"""Unit tests for Comment module - Mock-based testing.

Tests comment functionality using mocks instead of real database.
"""

from datetime import UTC, datetime
from uuid import uuid4
from unittest.mock import Mock, patch

import pytest

from app.core.tasks.comment_service import TaskCommentService


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock()


@pytest.fixture
def mock_event_publisher():
    """Mock event publisher."""
    return Mock()


@pytest.fixture
def task_comment_service(mock_db, mock_event_publisher):
    """Task comment service with mocked dependencies."""
    return TaskCommentService(mock_db, mock_event_publisher)


class TestTaskCommentServiceBasic:
    """Basic tests for TaskCommentService using mocks."""

    def test_add_comment_success(self, task_comment_service, mock_db):
        """Test adding a comment successfully."""
        # Arrange
        task_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()
        content = "Test comment"

        # Mock the database objects
        mock_task = Mock()
        mock_task.id = task_id
        mock_db.query.return_value.filter.return_value.first.return_value = mock_task

        mock_comment = Mock()
        mock_comment.id = uuid4()
        mock_comment.content = content
        mock_comment.created_at = datetime.now(UTC)
        mock_db.add.return_value = None
        mock_db.flush.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        # Mock Comment constructor
        with patch('app.core.tasks.comment_service.Comment') as mock_comment_class:
            mock_comment_class.return_value = mock_comment

            # Act
            result = task_comment_service.add_comment(
                task_id=task_id,
                tenant_id=tenant_id,
                user_id=user_id,
                content=content,
            )

        # Assert
        assert result is not None
        assert result["content"] == content
        assert result["task_id"] == str(task_id)
        assert "id" in result

        # Verify database operations
        mock_db.add.assert_called_once_with(mock_comment)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_comment)

        # Verify event was published
        task_comment_service.event_publisher.assert_called_once()

    def test_add_comment_task_not_found(self, task_comment_service, mock_db):
        """Test adding comment to non-existent task."""
        # Arrange
        task_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()
        content = "Test comment"

        # Mock task not found
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Task .* not found"):
            task_comment_service.add_comment(
                task_id=task_id,
                tenant_id=tenant_id,
                user_id=user_id,
                content=content,
            )

    def test_add_comment_empty_content(self, task_comment_service):
        """Test adding comment with empty content."""
        # Arrange
        task_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()
        content = ""

        # Act & Assert
        with pytest.raises(ValueError, match="Content cannot be empty"):
            task_comment_service.add_comment(
                task_id=task_id,
                tenant_id=tenant_id,
                user_id=user_id,
                content=content,
            )

    def test_add_comment_with_mentions(self, task_comment_service, mock_db):
        """Test adding a comment with mentions."""
        # Arrange
        task_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()
        mentioned_user_id = uuid4()
        content = "Hello @user!"
        mentions = [mentioned_user_id]

        # Mock task
        mock_task = Mock()
        mock_task.id = task_id
        mock_db.query.return_value.filter.return_value.first.return_value = mock_task

        # Mock comment
        mock_comment = Mock()
        mock_comment.id = uuid4()
        mock_comment.content = content
        mock_comment.created_at = datetime.now(UTC)

        # Mock Comment and CommentMention
        with patch('app.core.tasks.comment_service.Comment') as mock_comment_class, \
             patch('app.core.tasks.comment_service.CommentMention') as mock_comment_mention_class:

            mock_comment_class.return_value = mock_comment
            mock_mention = Mock()
            mock_comment_mention_class.return_value = mock_mention

            # Act
            result = task_comment_service.add_comment(
                task_id=task_id,
                tenant_id=tenant_id,
                user_id=user_id,
                content=content,
                mentions=mentions,
            )

        # Assert
        assert result is not None
        assert result["mentions"] == [str(mentioned_user_id)]

        # Verify mention was added
        mock_comment_mention_class.assert_called_once_with(
            tenant_id=tenant_id,
            comment_id=mock_comment.id,
            mentioned_user_id=mentioned_user_id,
            notification_sent=False,
        )
        mock_db.add.assert_called_with(mock_mention)

    def test_update_comment_success(self, task_comment_service, mock_db):
        """Test updating a comment successfully."""
        # Arrange
        task_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()
        comment_id = str(uuid4())
        new_content = "Updated content"

        # Mock existing comment
        mock_comment = Mock()
        mock_comment.id = comment_id
        mock_comment.created_by = user_id
        mock_comment.content = "Original content"
        mock_comment.is_edited = False
        mock_comment.mentions = []  # Mock empty mentions
        mock_db.query.return_value.filter.return_value.first.return_value = mock_comment

        # Act
        result = task_comment_service.update_comment(
            task_id=task_id,
            tenant_id=tenant_id,
            user_id=user_id,
            comment_id=comment_id,
            content=new_content,
        )

        # Assert
        assert result is not None
        assert result["content"] == new_content
        assert result["id"] == comment_id

        # Verify updates
        assert mock_comment.content == new_content
        assert mock_comment.is_edited is True
        assert mock_comment.edited_at is not None
        mock_db.commit.assert_called_once()

    def test_update_comment_not_found(self, task_comment_service, mock_db):
        """Test updating non-existent comment."""
        # Arrange
        task_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()
        comment_id = str(uuid4())
        new_content = "Updated content"

        # Mock comment not found
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Act
        result = task_comment_service.update_comment(
            task_id=task_id,
            tenant_id=tenant_id,
            user_id=user_id,
            comment_id=comment_id,
            content=new_content,
        )

        # Assert
        assert result is None

    def test_update_comment_unauthorized(self, task_comment_service, mock_db):
        """Test updating comment by non-author."""
        # Arrange
        task_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()
        author_id = uuid4()
        comment_id = str(uuid4())
        new_content = "Updated by other user"

        # Mock existing comment with different author
        mock_comment = Mock()
        mock_comment.id = comment_id
        mock_comment.created_by = author_id  # Different user
        mock_db.query.return_value.filter.return_value.first.return_value = mock_comment

        # Act
        result = task_comment_service.update_comment(
            task_id=task_id,
            tenant_id=tenant_id,
            user_id=user_id,
            comment_id=comment_id,
            content=new_content,
        )

        # Assert
        assert result is None

    def test_delete_comment_success(self, task_comment_service, mock_db):
        """Test deleting a comment successfully."""
        # Arrange
        task_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()
        comment_id = str(uuid4())

        # Mock existing comment
        mock_comment = Mock()
        mock_comment.id = comment_id
        mock_comment.created_by = user_id
        mock_comment.mentions = []  # Mock empty mentions
        mock_db.query.return_value.filter.return_value.first.return_value = mock_comment

        # Act
        result = task_comment_service.delete_comment(
            task_id=task_id,
            tenant_id=tenant_id,
            user_id=user_id,
            comment_id=comment_id,
        )

        # Assert
        assert result is True
        assert mock_comment.is_deleted is True
        assert mock_comment.deleted_at is not None
        mock_db.commit.assert_called_once()

    def test_delete_comment_not_found(self, task_comment_service, mock_db):
        """Test deleting non-existent comment."""
        # Arrange
        task_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()
        comment_id = str(uuid4())

        # Mock comment not found
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Act
        result = task_comment_service.delete_comment(
            task_id=task_id,
            tenant_id=tenant_id,
            user_id=user_id,
            comment_id=comment_id,
        )

        # Assert
        assert result is False

    def test_list_comments_success(self, task_comment_service, mock_db):
        """Test listing comments successfully."""
        # Arrange
        task_id = uuid4()
        tenant_id = uuid4()

        # Mock comments
        mock_comment1 = Mock()
        mock_comment1.id = uuid4()
        mock_comment1.content = "First comment"
        mock_comment1.created_at = datetime.now(UTC)
        mock_comment1.created_by = uuid4()
        mock_comment1.mentions = []  # Mock empty mentions

        mock_comment2 = Mock()
        mock_comment2.id = uuid4()
        mock_comment2.content = "Second comment"
        mock_comment2.created_at = datetime.now(UTC)
        mock_comment2.created_by = uuid4()
        mock_comment2.mentions = []  # Mock empty mentions

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            mock_comment2, mock_comment1  # Ordered by created_at desc
        ]

        # Act
        result = task_comment_service.list_comments(
            task_id=task_id,
            tenant_id=tenant_id,
        )

        # Assert
        assert len(result) == 2
        assert result[0]["content"] == "Second comment"
        assert result[1]["content"] == "First comment"

    def test_list_comments_empty(self, task_comment_service, mock_db):
        """Test listing comments when none exist."""
        # Arrange
        task_id = uuid4()
        tenant_id = uuid4()

        # Mock empty result
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        # Act
        result = task_comment_service.list_comments(
            task_id=task_id,
            tenant_id=tenant_id,
        )

        # Assert
        assert len(result) == 0
        assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
