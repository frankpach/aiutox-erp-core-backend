"""Unit tests for Async Tasks Service."""

from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from app.core.async_tasks.service import AsyncTaskService
from app.core.async_tasks.task import Task


class MockTask(Task):
    """Mock task for testing."""

    def __init__(self, module: str, name: str, execute_result=None):
        super().__init__(module, name)
        self.execute_result = execute_result or {"result": "success"}

    async def execute(self, tenant_id: UUID, **kwargs):
        return self.execute_result


class TestAsyncTaskService:
    """Tests for AsyncTaskService."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create AsyncTaskService instance."""
        return AsyncTaskService(mock_db)

    def test_get_all_tasks(self, service):
        """Test getting all registered tasks."""
        # Arrange
        registry = service.registry
        task = MockTask(module="test", name="test_task")
        registry.register(task, {"type": "interval", "hours": 24})

        # Act
        all_tasks = service.get_all_tasks()

        # Assert
        assert isinstance(all_tasks, dict)
        assert len(all_tasks) > 0

    def test_get_tasks_by_module(self, service):
        """Test getting tasks by module."""
        # Arrange
        registry = service.registry
        task = MockTask(module="files", name="cleanup_task")
        registry.register(task, {"type": "interval", "hours": 24})

        # Act
        files_tasks = service.get_tasks_by_module("files")

        # Assert
        assert isinstance(files_tasks, dict)
        assert "files.cleanup_task" in files_tasks

    @pytest.mark.asyncio
    async def test_execute_task_manually(self, service):
        """Test executing a task manually."""
        # Arrange
        tenant_id = uuid4()
        registry = service.registry
        task = MockTask(module="test", name="manual_task", execute_result={"executed": True})
        registry.register(task, {"type": "interval", "hours": 24})

        # Act
        result = await service.execute_task("test.manual_task", tenant_id)

        # Assert
        assert result["executed"] is True

    @pytest.mark.asyncio
    async def test_execute_task_not_found(self, service):
        """Test executing a non-existent task."""
        # Act & Assert
        with pytest.raises(ValueError, match="Task.*not found"):
            await service.execute_task("nonexistent.task", uuid4())

    @pytest.mark.asyncio
    async def test_start_scheduler(self, service):
        """Test starting the scheduler."""
        # Act
        await service.start_scheduler()

        # Assert
        assert service.scheduler._running is True

        # Cleanup
        await service.stop_scheduler()

    @pytest.mark.asyncio
    async def test_stop_scheduler(self, service):
        """Test stopping the scheduler."""
        # Arrange
        await service.start_scheduler()

        # Act
        await service.stop_scheduler()

        # Assert
        assert service.scheduler._running is False






