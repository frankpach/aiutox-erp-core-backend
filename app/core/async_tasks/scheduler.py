"""Scheduler for executing async tasks."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.async_tasks.registry import TaskRegistry, get_registry

logger = logging.getLogger(__name__)


class AsyncTaskScheduler:
    """Scheduler for executing async tasks."""

    def __init__(self, registry: TaskRegistry | None = None):
        """Initialize scheduler.

        Args:
            registry: Task registry (uses global registry if not provided)
        """
        self.registry = registry or get_registry()
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._scheduled_tasks: dict[str, dict[str, Any]] = {}

    async def schedule_task(
        self,
        task_id: str,
        schedule: dict[str, Any],
        tenant_id: UUID | None = None,
    ) -> None:
        """Schedule a task to be executed based on schedule.

        Args:
            task_id: Task ID (e.g., 'files.cleanup_deleted_files')
            schedule: Schedule configuration (e.g., {'type': 'interval', 'hours': 24})
            tenant_id: Optional tenant ID (if None, runs for all tenants)
        """
        task_config = self.registry.get_task(task_id)
        if not task_config:
            raise ValueError(f"Task {task_id} not found in registry")

        if not task_config["enabled"]:
            logger.info(f"Task {task_id} is disabled, skipping schedule")
            return

        schedule_type = schedule.get("type")

        if schedule_type == "interval":
            # Execute at regular intervals
            hours = schedule.get("hours", 24)
            seconds = schedule.get("seconds", hours * 3600)
            task = asyncio.create_task(
                self._interval_task(task_id, seconds, tenant_id)
            )
            self._tasks.append(task)
            self._scheduled_tasks[task_id] = {"schedule": schedule, "task": task}
        elif schedule_type == "cron":
            # Execute based on cron expression (future implementation)
            logger.warning("Cron-based scheduling not yet implemented")
        elif schedule_type == "once":
            # Execute once at a specific time
            execute_at = schedule.get("execute_at")
            if execute_at:
                task = asyncio.create_task(
                    self._once_task(task_id, execute_at, tenant_id)
                )
                self._tasks.append(task)
                self._scheduled_tasks[task_id] = {"schedule": schedule, "task": task}
        else:
            raise ValueError(f"Unknown schedule type: {schedule_type}")

        logger.info(f"Scheduled task {task_id} with schedule type: {schedule_type}")

    async def _interval_task(
        self, task_id: str, seconds: int, tenant_id: UUID | None
    ) -> None:
        """Task for interval-based scheduling.

        Args:
            task_id: Task ID
            seconds: Interval in seconds
            tenant_id: Optional tenant ID
        """
        while self._running:
            try:
                await asyncio.sleep(seconds)
                if self._running:
                    await self._execute_task(task_id, tenant_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Error in scheduled task for {task_id}: {e}", exc_info=True
                )

    async def _once_task(
        self, task_id: str, execute_at: str, tenant_id: UUID | None
    ) -> None:
        """Task for one-time scheduling.

        Args:
            task_id: Task ID
            execute_at: ISO format datetime string
            tenant_id: Optional tenant ID
        """
        try:
            target_time = datetime.fromisoformat(execute_at.replace("Z", "+00:00"))
            now = datetime.now(UTC)

            if target_time > now:
                wait_seconds = (target_time - now).total_seconds()
                await asyncio.sleep(wait_seconds)
                if self._running:
                    await self._execute_task(task_id, tenant_id)
            else:
                logger.warning(
                    f"Scheduled time {execute_at} is in the past for task {task_id}"
                )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in one-time task for {task_id}: {e}", exc_info=True)

    async def _execute_task(self, task_id: str, tenant_id: UUID | None) -> None:
        """Execute a task.

        Args:
            task_id: Task ID
            tenant_id: Optional tenant ID
        """
        task_config = self.registry.get_task(task_id)
        if not task_config:
            logger.error(f"Task {task_id} not found")
            return

        task_instance = task_config["task"]

        try:
            if tenant_id:
                # Execute for specific tenant
                result = await task_instance.execute(tenant_id)
                logger.info(f"Task {task_id} executed for tenant {tenant_id}: {result}")
            else:
                # Execute for all tenants
                from app.core.db.session import SessionLocal
                from app.models.tenant import Tenant

                db = SessionLocal()
                try:
                    tenants = db.query(Tenant).all()
                    for tenant in tenants:
                        try:
                            result = await task_instance.execute(tenant.id)
                            logger.info(
                                f"Task {task_id} executed for tenant {tenant.id}: {result}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Error executing task {task_id} for tenant {tenant.id}: {e}",
                                exc_info=True,
                            )
                finally:
                    db.close()
        except Exception as e:
            logger.error(
                f"Error executing task {task_id}: {e}", exc_info=True
            )

    def cancel_task(self, task_id: str) -> None:
        """Cancel a scheduled task.

        Args:
            task_id: Task ID
        """
        if task_id in self._scheduled_tasks:
            task = self._scheduled_tasks[task_id]["task"]
            task.cancel()
            del self._scheduled_tasks[task_id]
            logger.info(f"Cancelled scheduled task {task_id}")

    async def start(self) -> None:
        """Start the scheduler and schedule all registered tasks."""
        self._running = True

        # Schedule all registered tasks
        all_tasks = self.registry.get_all_tasks()
        for task_id, task_config in all_tasks.items():
            if task_config["enabled"]:
                try:
                    await self.schedule_task(
                        task_id,
                        task_config["schedule"],
                        tenant_id=None,  # Will be handled per-tenant in future
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to schedule task {task_id}: {e}", exc_info=True
                    )

        logger.info("AsyncTaskScheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self._scheduled_tasks.clear()
        logger.info("AsyncTaskScheduler stopped")

