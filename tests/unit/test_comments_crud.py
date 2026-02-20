"""Unit tests for Comment module - Complete CRUD testing across different entities.

Tests comment functionality for:
- Tasks
- Products
- General entities
"""

import hashlib
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.tasks.comment_service import TaskCommentService
from app.models.comment import Comment, CommentMention
from app.models.task import Task
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.products.models.product import Product
from tests.conftest import TestingSessionLocal


@pytest.fixture
def db(setup_database):
    """Database session fixture."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def mock_event_publisher():
    """Mock event publisher fixture."""
    return Mock()


@pytest.fixture
def task_comment_service(db, mock_event_publisher):
    """Task comment service fixture."""
    return TaskCommentService(db, mock_event_publisher)


@pytest.fixture
def sample_tenant(db):
    """Create sample tenant."""
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug=f"test-tenant-comments-{uuid4().hex[:8]}",
        is_active=True,
    )
    db.add(tenant)
    db.commit()
    return tenant


@pytest.fixture
def sample_user(db, sample_tenant):
    """Create sample user."""
    password_hash = hashlib.sha256(b"test123").hexdigest()
    user = User(
        id=uuid4(),
        tenant_id=sample_tenant.id,
        email=f"test-{uuid4().hex[:8]}@example.com",
        full_name="Test User",
        password_hash=password_hash,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def sample_task(db, sample_user):
    """Create sample task."""
    task = Task(
        id=uuid4(),
        tenant_id=sample_user.tenant_id,
        title="Sample Task",
        description="Test task description",
        created_by_id=sample_user.id,
    )
    db.add(task)
    db.commit()
    return task


@pytest.fixture
def sample_product(db, sample_user):
    """Create sample product."""
    product = Product(
        id=uuid4(),
        tenant_id=sample_user.tenant_id,
        name="Sample Product",
        description="Test product description",
        sku=f"TEST-{uuid4().hex[:6]}",
    )
    db.add(product)
    db.commit()
    return product




class TestTaskComments:
    """Test task comments CRUD operations."""

    def test_add_comment_success(self, task_comment_service, sample_task, sample_user):
        """Test adding a comment to a task."""
        # Arrange
        content = "This is a test comment"

        # Act
        result = task_comment_service.add_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=sample_user.id,
            content=content,
        )

        # Assert
        assert result is not None
        assert result["content"] == content
        assert result["user_id"] == str(sample_user.id)
        assert "id" in result
        assert "created_at" in result

        # Verify in database
        comment = task_comment_service.db.query(Comment).filter(
            Comment.entity_id == sample_task.id,
            Comment.entity_type == "task"
        ).first()
        assert comment is not None
        assert comment.content == content
        assert comment.created_by == sample_user.id

    def test_add_comment_with_mentions(self, task_comment_service, sample_task, sample_user, db):
        """Test adding a comment with mentions."""
        # Arrange
        password_hash = hashlib.sha256(b"test123").hexdigest()
        mentioned_user = User(
            id=uuid4(),
            tenant_id=sample_user.tenant_id,
            email=f"mentioned-{uuid4().hex[:8]}@example.com",
            full_name="Mentioned User",
            password_hash=password_hash,
            is_active=True,
        )
        db.add(mentioned_user)
        db.commit()

        content = "Hello @mentioned user!"
        mentions = [mentioned_user.id]

        # Act
        result = task_comment_service.add_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=sample_user.id,
            content=content,
            mentions=mentions,
        )

        # Assert
        assert result is not None
        assert len(result["mentions"]) == 1
        assert str(mentioned_user.id) in result["mentions"]

        # Verify mentions in database
        mention = task_comment_service.db.query(CommentMention).filter(
            CommentMention.comment_id == result["id"]
        ).first()
        assert mention is not None
        assert mention.mentioned_user_id == mentioned_user.id

    def test_update_comment_success(self, task_comment_service, sample_task, sample_user):
        """Test updating a comment."""
        # Arrange - Create comment first
        original_content = "Original comment"
        comment = task_comment_service.add_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=sample_user.id,
            content=original_content,
        )

        # Act
        updated_content = "Updated comment"
        result = task_comment_service.update_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=sample_user.id,
            comment_id=comment["id"],
            content=updated_content,
        )

        # Assert
        assert result is not None
        assert result["content"] == updated_content
        assert result["id"] == comment["id"]

        # Verify in database
        db_comment = task_comment_service.db.query(Comment).filter(
            Comment.id == comment["id"]
        ).first()
        assert db_comment is not None
        assert db_comment.content == updated_content
        assert db_comment.is_edited is True

    def test_update_comment_unauthorized(self, task_comment_service, sample_task, sample_user, db):
        """Test updating a comment by non-author."""
        # Arrange
        import hashlib
        other_user = User(
            id=uuid4(),
            tenant_id=sample_user.tenant_id,
            email=f"other-{uuid4().hex[:8]}@example.com",
            full_name="Other User",
            password_hash=hashlib.sha256(b"test123").hexdigest(),
            is_active=True,
        )
        db.add(other_user)
        db.commit()

        comment = task_comment_service.add_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=sample_user.id,
            content="Original comment",
        )

        # Act
        result = task_comment_service.update_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=other_user.id,
            comment_id=comment["id"],
            content="Updated by other user",
        )

        # Assert
        assert result is None

    def test_delete_comment_success(self, task_comment_service, sample_task, sample_user):
        """Test deleting a comment."""
        # Arrange
        comment = task_comment_service.add_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=sample_user.id,
            content="To be deleted",
        )
        comment_id = comment["id"]

        # Act
        result = task_comment_service.delete_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=sample_user.id,
            comment_id=comment_id,
        )

        # Assert
        assert result is True

        # Verify soft delete in database
        db_comment = task_comment_service.db.query(Comment).filter(
            Comment.id == comment_id
        ).first()
        assert db_comment is not None
        assert db_comment.is_deleted is True
        assert db_comment.deleted_at is not None

    def test_delete_comment_unauthorized(self, task_comment_service, sample_task, sample_user, db):
        """Test deleting a comment by non-author."""
        # Arrange
        import hashlib
        other_user = User(
            id=uuid4(),
            tenant_id=sample_user.tenant_id,
            email=f"other-{uuid4().hex[:8]}@example.com",
            full_name="Other User",
            password_hash=hashlib.sha256(b"test123").hexdigest(),
            is_active=True,
        )
        db.add(other_user)
        db.commit()

        comment = task_comment_service.add_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=sample_user.id,
            content="Cannot be deleted by others",
        )

        # Act
        result = task_comment_service.delete_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=other_user.id,
            comment_id=comment["id"],
        )

        # Assert
        assert result is False

    def test_list_comments(self, task_comment_service, sample_task, sample_user):
        """Test listing comments for a task."""
        # Arrange - Create multiple comments
        comments_data = [
            "First comment",
            "Second comment",
            "Third comment",
        ]

        for content in comments_data:
            task_comment_service.add_comment(
                task_id=sample_task.id,
                tenant_id=sample_task.tenant_id,
                user_id=sample_user.id,
                content=content,
            )

        # Act
        result = task_comment_service.list_comments(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
        )

        # Assert
        assert len(result) == 3
        # Should be ordered by created_at desc (newest first)
        assert result[0]["content"] == "Third comment"
        assert result[1]["content"] == "Second comment"
        assert result[2]["content"] == "First comment"

    def test_list_comments_excludes_deleted(self, task_comment_service, sample_task, sample_user):
        """Test that deleted comments are not listed."""
        # Arrange
        _ = task_comment_service.add_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=sample_user.id,
            content="Active comment",
        )

        comment2 = task_comment_service.add_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=sample_user.id,
            content="Deleted comment",
        )

        # Delete one comment
        task_comment_service.delete_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=sample_user.id,
            comment_id=comment2["id"],
        )

        # Act
        result = task_comment_service.list_comments(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
        )

        # Assert
        assert len(result) == 1
        assert result[0]["content"] == "Active comment"


class TestCrossEntityComments:
    """Test comments across different entity types."""

    def test_product_comments(self, task_comment_service, sample_product, sample_user):
        """Test comments on products."""
        # Use task_comment_service but with product entity
        content = "Great product!"

        # Direct database manipulation for cross-entity test
        comment = Comment(
            tenant_id=sample_product.tenant_id,
            entity_type="product",
            entity_id=sample_product.id,
            content=content,
            created_by=sample_user.id,
            is_edited=False,
            is_deleted=False,
        )

        task_comment_service.db.add(comment)
        task_comment_service.db.commit()

        # Verify
        assert comment.id is not None
        assert comment.entity_type == "product"
        assert comment.entity_id == sample_product.id

    def test_list_comments_by_entity_type(self, task_comment_service, db, sample_task, sample_product, sample_user):
        """Test listing comments filtered by entity type."""
        # Create comments for different entities
        task_comment = Comment(
            tenant_id=sample_task.tenant_id,
            entity_type="task",
            entity_id=sample_task.id,
            content="Task comment",
            created_by=sample_user.id,
            is_edited=False,
            is_deleted=False,
        )

        product_comment = Comment(
            tenant_id=sample_product.tenant_id,
            entity_type="product",
            entity_id=sample_product.id,
            content="Product comment",
            created_by=sample_user.id,
            is_edited=False,
            is_deleted=False,
        )

        db.add(task_comment)
        db.add(product_comment)
        db.commit()

        # Query task comments
        task_comments = db.query(Comment).filter(
            Comment.entity_type == "task",
            Comment.tenant_id == sample_task.tenant_id,
            Comment.is_deleted == False
        ).all()

        # Query product comments
        product_comments = db.query(Comment).filter(
            Comment.entity_type == "product",
            Comment.tenant_id == sample_product.tenant_id,
            Comment.is_deleted == False
        ).all()

        # Assert
        assert len(task_comments) == 1
        assert len(product_comments) == 1
        assert task_comments[0].content == "Task comment"
        assert product_comments[0].content == "Product comment"


class TestCommentValidation:
    """Test comment validation and edge cases."""

    def test_empty_content_validation(self, task_comment_service, sample_task, sample_user):
        """Test validation for empty content."""
        # Act & Assert
        with pytest.raises(ValueError, match="Content cannot be empty"):
            task_comment_service.add_comment(
                task_id=sample_task.id,
                tenant_id=sample_task.tenant_id,
                user_id=sample_user.id,
                content="",
            )

    def test_nonexistent_task(self, task_comment_service, sample_user):
        """Test adding comment to non-existent task."""
        # Act & Assert
        with pytest.raises(ValueError, match="Task .* not found"):
            task_comment_service.add_comment(
                task_id=uuid4(),
                tenant_id=sample_user.tenant_id,
                user_id=sample_user.id,
                content="Comment on non-existent task",
            )

    def test_update_nonexistent_comment(self, task_comment_service, sample_task, sample_user):
        """Test updating non-existent comment."""
        # Act
        result = task_comment_service.update_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=sample_user.id,
            comment_id=str(uuid4()),
            content="Updated content",
        )

        # Assert
        assert result is None

    def test_delete_nonexistent_comment(self, task_comment_service, sample_task, sample_user):
        """Test deleting non-existent comment."""
        # Act
        result = task_comment_service.delete_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=sample_user.id,
            comment_id=str(uuid4()),
        )

        # Assert
        assert result is False


class TestCommentEvents:
    """Test comment-related events."""

    def test_comment_added_event(self, task_comment_service, sample_task, sample_user, mock_event_publisher):
        """Test that comment_added event is published."""
        # Act
        task_comment_service.add_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=sample_user.id,
            content="Test comment",
        )

        # Assert
        mock_event_publisher.publish.assert_called_once()
        call_args = mock_event_publisher.publish.call_args
        assert call_args.kwargs["event_type"] == "task.comment_added"
        assert call_args.kwargs["entity_type"] == "task"
        assert call_args.kwargs["entity_id"] == sample_task.id
        assert call_args.kwargs["tenant_id"] == sample_task.tenant_id
        assert call_args.kwargs["user_id"] == sample_user.id

    def test_comment_updated_event(self, task_comment_service, sample_task, sample_user, mock_event_publisher):
        """Test that comment_updated event is published."""
        # Arrange
        comment = task_comment_service.add_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=sample_user.id,
            content="Original",
        )

        # Reset mock to capture only update event
        mock_event_publisher.reset_mock()

        # Act
        task_comment_service.update_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=sample_user.id,
            comment_id=comment["id"],
            content="Updated",
        )

        # Assert
        mock_event_publisher.publish.assert_called_once()
        call_args = mock_event_publisher.publish.call_args
        assert call_args.kwargs["event_type"] == "task.comment_updated"
        assert call_args.kwargs["entity_type"] == "task"
        assert call_args.kwargs["entity_id"] == sample_task.id
        assert call_args.kwargs["tenant_id"] == sample_task.tenant_id
        assert call_args.kwargs["user_id"] == sample_user.id

    def test_comment_deleted_event(self, task_comment_service, sample_task, sample_user, mock_event_publisher):
        """Test that comment_deleted event is published."""
        # Arrange
        comment = task_comment_service.add_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=sample_user.id,
            content="To be deleted",
        )

        # Reset mock to capture only delete event
        mock_event_publisher.reset_mock()

        # Act
        task_comment_service.delete_comment(
            task_id=sample_task.id,
            tenant_id=sample_task.tenant_id,
            user_id=sample_user.id,
            comment_id=comment["id"],
        )

        # Assert
        mock_event_publisher.publish.assert_called_once()
        call_args = mock_event_publisher.publish.call_args
        assert call_args.kwargs["event_type"] == "task.comment_deleted"
        assert call_args.kwargs["entity_type"] == "task"
        assert call_args.kwargs["entity_id"] == sample_task.id
        assert call_args.kwargs["tenant_id"] == sample_task.tenant_id
        assert call_args.kwargs["user_id"] == sample_user.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
