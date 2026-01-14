"""Base task class for async tasks."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class Task(ABC):
    """Base class for async tasks."""

    def __init__(
        self,
        module: str,
        name: str,
        description: str | None = None,
    ):
        """Initialize task.

        Args:
            module: Module name (e.g., 'files', 'notifications')
            name: Task name (e.g., 'cleanup_deleted_files')
            description: Task description
        """
        self.module = module
        self.name = name
        self.description = description
        self.task_id = f"{module}.{name}"

    @abstractmethod
    async def execute(self, tenant_id: UUID, **kwargs) -> dict[str, Any]:
        """Execute the task.

        Args:
            tenant_id: Tenant ID
            **kwargs: Additional task-specific parameters

        Returns:
            Dict with task execution results
        """
        pass

    def __repr__(self) -> str:
        return f"<Task(module={self.module}, name={self.name})>"






