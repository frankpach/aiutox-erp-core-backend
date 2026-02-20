"""Unit tests for Async Tasks Registry."""

from uuid import UUID

from app.core.async_tasks.registry import TaskRegistry, get_registry
from app.core.async_tasks.task import Task


class MockTask(Task):
    """Mock task for testing."""

    async def execute(self, tenant_id: UUID, **kwargs):
        return {"result": "success"}


class TestTaskRegistry:
    """Tests for TaskRegistry."""

    def test_registry_singleton(self):
        """Test that registry is a singleton."""
        registry1 = TaskRegistry()
        registry2 = TaskRegistry()
        assert registry1 is registry2

    def test_register_task(self):
        """Test registering a task."""
        # Arrange
        registry = TaskRegistry()
        task = MockTask(module="test", name="test_task", description="Test task")
        schedule = {"type": "interval", "hours": 24}

        # Act
        registry.register(task, schedule, enabled=True)

        # Assert
        task_config = registry.get_task("test.test_task")
        assert task_config is not None
        assert task_config["task"] == task
        assert task_config["schedule"] == schedule
        assert task_config["enabled"] is True

    def test_get_task_not_found(self):
        """Test getting a non-existent task."""
        # Arrange
        registry = TaskRegistry()

        # Act
        task_config = registry.get_task("nonexistent.task")

        # Assert
        assert task_config is None

    def test_get_all_tasks(self):
        """Test getting all registered tasks."""
        # Arrange
        registry = TaskRegistry()
        task1 = MockTask(module="test", name="task1")
        task2 = MockTask(module="test", name="task2")
        schedule = {"type": "interval", "hours": 24}

        # Act
        registry.register(task1, schedule)
        registry.register(task2, schedule)

        all_tasks = registry.get_all_tasks()

        # Assert
        assert len(all_tasks) >= 2
        assert "test.task1" in all_tasks
        assert "test.task2" in all_tasks

    def test_get_tasks_by_module(self):
        """Test getting tasks by module."""
        # Arrange
        registry = TaskRegistry()
        task1 = MockTask(module="files", name="task1")
        task2 = MockTask(module="notifications", name="task2")
        schedule = {"type": "interval", "hours": 24}

        registry.register(task1, schedule)
        registry.register(task2, schedule)

        # Act
        files_tasks = registry.get_tasks_by_module("files")

        # Assert
        assert len(files_tasks) >= 1
        assert "files.task1" in files_tasks
        assert "notifications.task2" not in files_tasks

    def test_unregister_task(self):
        """Test unregistering a task."""
        # Arrange
        registry = TaskRegistry()
        task = MockTask(module="test", name="test_task")
        schedule = {"type": "interval", "hours": 24}
        registry.register(task, schedule)

        # Act
        registry.unregister("test.test_task")

        # Assert
        task_config = registry.get_task("test.test_task")
        assert task_config is None

    def test_register_task_decorator(self):
        """Test register_task decorator."""
        # Arrange
        from app.core.async_tasks.registry import register_task

        @register_task(
            module="test",
            name="decorated_task",
            schedule={"type": "interval", "hours": 12},
            description="Decorated task",
            enabled=True,
        )
        class DecoratedTask(Task):
            async def execute(self, tenant_id: UUID, **kwargs):
                return {}

        # Act
        registry = get_registry()
        task_config = registry.get_task("test.decorated_task")

        # Assert
        assert task_config is not None
        assert task_config["task"].name == "decorated_task"
        assert task_config["schedule"]["hours"] == 12
        assert task_config["enabled"] is True
