"""Unit tests for TaskService."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.pubsub import EventPublisher
from app.core.tasks.service import TaskService
from app.models.task import TaskPriority, TaskStatus


@pytest.fixture
def mock_event_publisher():
    """Create a mock EventPublisher."""
    publisher = MagicMock(spec=EventPublisher)
    publisher.publish = AsyncMock(return_value="message-id-123")
    return publisher


@pytest.fixture
def task_service(db_session, mock_event_publisher):
    """Create TaskService instance."""
    return TaskService(db=db_session, event_publisher=mock_event_publisher)


@pytest.mark.asyncio
async def test_create_task(task_service, test_user, test_tenant, mock_event_publisher):
    """Test creating a task."""
    task = await task_service.create_task(
        title="Test Task",
        tenant_id=test_tenant.id,
        created_by_id=test_user.id,
        description="Test description",
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
    )

    assert task.title == "Test Task"
    assert task.description == "Test description"
    assert task.status == TaskStatus.TODO
    assert task.priority == TaskPriority.HIGH
    assert task.tenant_id == test_tenant.id
    assert task.created_by_id == test_user.id

    # Verify event was published
    assert mock_event_publisher.publish.called


@pytest.mark.asyncio
async def test_get_task(task_service, test_user, test_tenant):
    """Test getting a task."""
    # Create a task first
    task = await task_service.create_task(
        title="Test Task",
        tenant_id=test_tenant.id,
        created_by_id=test_user.id,
    )

    # Get it
    retrieved_task = task_service.get_task(task.id, test_tenant.id)

    assert retrieved_task is not None
    assert retrieved_task.id == task.id
    assert retrieved_task.title == "Test Task"


@pytest.mark.asyncio
async def test_get_task_not_found(task_service, test_tenant):
    """Test getting a non-existent task."""
    task_id = uuid4()
    task = task_service.get_task(task_id, test_tenant.id)

    assert task is None


@pytest.mark.asyncio
async def test_get_tasks(task_service, test_user, test_tenant):
    """Test getting tasks with filters."""
    # Create multiple tasks
    task1 = await task_service.create_task(
        title="Task 1",
        tenant_id=test_tenant.id,
        created_by_id=test_user.id,
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
    )
    task2 = await task_service.create_task(
        title="Task 2",
        tenant_id=test_tenant.id,
        created_by_id=test_user.id,
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.MEDIUM,
    )

    # Get all tasks
    tasks = task_service.get_tasks(test_tenant.id)
    assert len(tasks) >= 2
    assert any(t.id == task2.id for t in tasks)

    # Filter by status
    todo_tasks = task_service.get_tasks(test_tenant.id, status=TaskStatus.TODO)
    assert any(t.id == task1.id for t in todo_tasks)

    # Filter by priority
    high_priority_tasks = task_service.get_tasks(test_tenant.id, priority=TaskPriority.HIGH)
    assert any(t.id == task1.id for t in high_priority_tasks)


@pytest.mark.asyncio
async def test_update_task(task_service, test_user, test_tenant, mock_event_publisher):
    """Test updating a task."""
    # Create a task
    task = await task_service.create_task(
        title="Original Title",
        tenant_id=test_tenant.id,
        created_by_id=test_user.id,
        status=TaskStatus.TODO,
    )

    # Update it
    updated_task = task_service.update_task(
        task.id,
        test_tenant.id,
        {"title": "Updated Title", "status": TaskStatus.IN_PROGRESS},
        test_user.id,
    )

    assert updated_task is not None
    assert updated_task.title == "Updated Title"
    assert updated_task.status == TaskStatus.IN_PROGRESS



@pytest.mark.asyncio
async def test_update_task_to_done(task_service, test_user, test_tenant):
    """Test updating task status to DONE sets completed_at."""
    # Create a task
    task = await task_service.create_task(
        title="Test Task",
        tenant_id=test_tenant.id,
        created_by_id=test_user.id,
        status=TaskStatus.TODO,
    )

    assert task.completed_at is None

    # Transition to IN_PROGRESS first
    task_service.update_task(
        task.id,
        test_tenant.id,
        {"status": TaskStatus.IN_PROGRESS},
        test_user.id,
    )

    # Update to DONE
    updated_task = task_service.update_task(
        task.id,
        test_tenant.id,
        {"status": TaskStatus.DONE},
        test_user.id,
    )

    assert updated_task is not None
    assert updated_task.status == TaskStatus.DONE
    assert updated_task.completed_at is not None


@pytest.mark.asyncio
async def test_delete_task(task_service, test_user, test_tenant, mock_event_publisher):
    """Test deleting a task."""
    # Create a task
    task = await task_service.create_task(
        title="Test Task",
        tenant_id=test_tenant.id,
        created_by_id=test_user.id,
    )

    # Delete it
    deleted = await task_service.delete_task(task.id, test_tenant.id, test_user.id)

    assert deleted is True

    # Verify it's deleted
    retrieved_task = task_service.get_task(task.id, test_tenant.id)
    assert retrieved_task is None

    # Verify event was published
    publish_calls = [call for call in mock_event_publisher.publish.call_args_list]
    delete_calls = [
        call for call in publish_calls if call[1].get("event_type") == "task.deleted"
    ]
    assert len(delete_calls) > 0


@pytest.mark.asyncio
async def test_add_checklist_item(task_service, test_user, test_tenant):
    """Test adding a checklist item to a task."""
    # Create a task
    task = await task_service.create_task(
        title="Test Task",
        tenant_id=test_tenant.id,
        created_by_id=test_user.id,
    )

    # Add checklist item
    item = task_service.add_checklist_item(
        task_id=task.id,
        tenant_id=test_tenant.id,
        title="Checklist Item 1",
        order=0,
    )

    assert item.title == "Checklist Item 1"
    assert item.task_id == task.id
    assert item.completed is False
    assert item.order == 0


@pytest.mark.asyncio
async def test_get_checklist_items(task_service, test_user, test_tenant):
    """Test getting checklist items for a task."""
    # Create a task
    task = await task_service.create_task(
        title="Test Task",
        tenant_id=test_tenant.id,
        created_by_id=test_user.id,
    )

    # Add multiple checklist items
    item1 = task_service.add_checklist_item(
        task_id=task.id, tenant_id=test_tenant.id, title="Item 1", order=0
    )
    item2 = task_service.add_checklist_item(
        task_id=task.id, tenant_id=test_tenant.id, title="Item 2", order=1
    )

    # Get all items
    items = task_service.get_checklist_items(task.id, test_tenant.id)

    assert len(items) >= 2
    assert any(i.id == item1.id for i in items)
    assert any(i.id == item2.id for i in items)


@pytest.mark.asyncio
async def test_update_checklist_item(task_service, test_user, test_tenant):
    """Test updating a checklist item."""
    task = await task_service.create_task(
        title="Test Task",
        tenant_id=test_tenant.id,
        created_by_id=test_user.id,
    )

    item = task_service.add_checklist_item(
        task_id=task.id, tenant_id=test_tenant.id, title="Item 1", order=0
    )

    updated_item = task_service.update_checklist_item(
        item.id, test_tenant.id, {"completed": True, "title": "Updated Item"}
    )

    assert updated_item is not None
    assert updated_item.completed is True
    assert updated_item.title == "Updated Item"


@pytest.mark.asyncio
async def test_delete_checklist_item(task_service, test_user, test_tenant):
    """Test deleting a checklist item."""
    task = await task_service.create_task(
        title="Test Task",
        tenant_id=test_tenant.id,
        created_by_id=test_user.id,
    )

    item = task_service.add_checklist_item(
        task_id=task.id, tenant_id=test_tenant.id, title="Item 1", order=0
    )

    deleted = task_service.delete_checklist_item(item.id, test_tenant.id)

    assert deleted is True

    items = task_service.get_checklist_items(task.id, test_tenant.id)
    assert not any(i.id == item.id for i in items)


