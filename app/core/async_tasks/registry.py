"""Task registry for registering and managing async tasks."""

import logging
from typing import Any

from app.core.async_tasks.task import Task

logger = logging.getLogger(__name__)


class TaskRegistry:
    """Central registry for async tasks."""

    _instance: "TaskRegistry | None" = None
    _tasks: dict[str, dict[str, Any]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(
        self,
        task: Task,
        schedule: dict[str, Any],
        enabled: bool = True,
    ) -> None:
        """Register a task.

        Args:
            task: Task instance
            schedule: Schedule configuration (e.g., {'type': 'interval', 'hours': 24})
            enabled: Whether task is enabled
        """
        self._tasks[task.task_id] = {
            "task": task,
            "schedule": schedule,
            "enabled": enabled,
        }
        logger.info(f"Registered task: {task.task_id}")

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        """Get a registered task.

        Args:
            task_id: Task ID (e.g., 'files.cleanup_deleted_files')

        Returns:
            Task configuration or None
        """
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> dict[str, dict[str, Any]]:
        """Get all registered tasks.

        Returns:
            Dict of all registered tasks
        """
        return self._tasks.copy()

    def get_tasks_by_module(self, module: str) -> dict[str, dict[str, Any]]:
        """Get all tasks for a module.

        Args:
            module: Module name

        Returns:
            Dict of tasks for the module
        """
        return {
            task_id: task_config
            for task_id, task_config in self._tasks.items()
            if task_config["task"].module == module
        }

    def unregister(self, task_id: str) -> None:
        """Unregister a task.

        Args:
            task_id: Task ID
        """
        if task_id in self._tasks:
            del self._tasks[task_id]
            logger.info(f"Unregistered task: {task_id}")


# Global registry instance
_registry = TaskRegistry()


def get_registry() -> TaskRegistry:
    """Get global task registry."""
    return _registry


def register_task(
    module: str,
    name: str,
    schedule: dict[str, Any],
    description: str | None = None,
    enabled: bool = True,
):
    """Decorator to register a task.

    Args:
        module: Module name
        name: Task name
        schedule: Schedule configuration
        description: Task description
        enabled: Whether task is enabled

    Usage:
        @register_task(
            module="files",
            name="cleanup_deleted_files",
            schedule={"type": "interval", "hours": 24},
            description="Clean up deleted files"
        )
        class CleanupDeletedFilesTask(Task):
            ...
    """
    def decorator(task_class: type[Task]):
        task_instance = task_class(module, name, description)
        _registry.register(task_instance, schedule, enabled)
        return task_class
    return decorator






