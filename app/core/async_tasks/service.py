"""Service for managing async tasks."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.async_tasks.registry import TaskRegistry, get_registry
from app.core.async_tasks.scheduler import AsyncTaskScheduler

logger = logging.getLogger(__name__)


class AsyncTaskService:
    """Service for managing async tasks."""

    def __init__(self, db: Session, registry: TaskRegistry | None = None):
        """Initialize async task service.

        Args:
            db: Database session
            registry: Task registry (uses global registry if not provided)
        """
        self.db = db
        self.registry = registry or get_registry()
        self.scheduler = AsyncTaskScheduler(self.registry)

    def get_all_tasks(self) -> dict[str, dict[str, Any]]:
        """Get all registered tasks.

        Returns:
            Dict of all registered tasks
        """
        return self.registry.get_all_tasks()

    def get_tasks_by_module(self, module: str) -> dict[str, dict[str, Any]]:
        """Get all tasks for a module.

        Args:
            module: Module name

        Returns:
            Dict of tasks for the module
        """
        return self.registry.get_tasks_by_module(module)

    async def execute_task(
        self, task_id: str, tenant_id: UUID, **kwargs
    ) -> dict[str, Any]:
        """Execute a task manually.

        Args:
            task_id: Task ID
            tenant_id: Tenant ID
            **kwargs: Additional task-specific parameters

        Returns:
            Task execution results
        """
        task_config = self.registry.get_task(task_id)
        if not task_config:
            raise ValueError(f"Task {task_id} not found")

        task_instance = task_config["task"]
        return await task_instance.execute(tenant_id, **kwargs)

    async def start_scheduler(self) -> None:
        """Start the task scheduler."""
        await self.scheduler.start()

    async def stop_scheduler(self) -> None:
        """Stop the task scheduler."""
        await self.scheduler.stop()




