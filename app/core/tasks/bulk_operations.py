"""Bulk operations service for Tasks module."""

from datetime import datetime
from uuid import UUID

from app.core.logging import get_logger
from app.core.tasks.cache_invalidation import task_cache_invalidation_service
from app.core.tasks.notification_service import task_notification_service
from app.models.task import TaskPriority, TaskStatusEnum
from app.repositories.task_repository import TaskRepository

logger = get_logger(__name__)


class BulkTaskOperation:
    """Represents a bulk task operation."""

    def __init__(
        self,
        operation_type: str,
        task_ids: list[UUID],
        user_id: UUID,
        tenant_id: UUID,
        **kwargs,
    ):
        self.operation_type = operation_type
        self.task_ids = task_ids
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.kwargs = kwargs
        self.results = []
        self.errors = []


class BulkTaskService:
    """Service for bulk task operations."""

    def __init__(self, db):
        """Initialize bulk task service."""
        self.db = db
        self.repository = TaskRepository(db)
        self.cache_invalidation = task_cache_invalidation_service
        self.notification_service = task_notification_service

    async def bulk_update_status(
        self, task_ids: list[UUID], new_status: str, user_id: UUID, tenant_id: UUID
    ) -> BulkTaskOperation:
        """Bulk update task status."""
        operation = BulkTaskOperation(
            "bulk_update_status", task_ids, user_id, tenant_id, new_status=new_status
        )

        try:
            # Validate status
            try:
                TaskStatusEnum(new_status)
            except ValueError:
                raise ValueError(f"Invalid status: {new_status}")

            # Get tasks
            tasks = self.repository.get_tasks_by_ids(tenant_id, task_ids)

            # Update each task
            for task in tasks:
                try:
                    old_status = task.status

                    # Validate status transition
                    from app.core.tasks.state_machine import TaskStateMachine

                    state_machine = TaskStateMachine()

                    if not state_machine.can_transition(old_status, new_status):
                        operation.errors.append(
                            {
                                "task_id": str(task.id),
                                "error": f"Invalid status transition from {old_status} to {new_status}",
                            }
                        )
                        continue

                    # Update task
                    task.status = new_status
                    if new_status == "done":
                        task.completed_at = datetime.utcnow()

                    updated_task = self.repository.update_task(
                        task.id,
                        {
                            "status": new_status,
                            "completed_at": (
                                task.completed_at if new_status == "done" else None
                            ),
                            "updated_by_id": user_id,
                        },
                    )

                    operation.results.append(
                        {
                            "task_id": str(task.id),
                            "old_status": old_status,
                            "new_status": new_status,
                            "success": True,
                        }
                    )

                    # Send notification
                    await self.notification_service.notify_task_status_changed(
                        updated_task, old_status, new_status, user_id
                    )

                    # Invalidate cache
                    await self.cache_invalidation.invalidate_on_status_change(
                        tenant_id,
                        task.id,
                        old_status,
                        new_status,
                        user_id,
                        task.assigned_to_id,
                        task.created_by_id,
                    )

                except Exception as e:
                    logger.error(f"Failed to update task {task.id}: {e}")
                    operation.errors.append({"task_id": str(task.id), "error": str(e)})

            # Invalidate bulk cache
            affected_users = {user_id}
            for task in tasks:
                if task.assigned_to_id:
                    affected_users.add(task.assigned_to_id)
                if task.created_by_id:
                    affected_users.add(task.created_by_id)

            await self.cache_invalidation.invalidate_on_bulk_operations(
                tenant_id, list(affected_users)
            )

        except Exception as e:
            logger.error(f"Bulk status update failed: {e}")
            operation.errors.append({"error": str(e)})

        return operation

    async def bulk_assign(
        self, task_ids: list[UUID], assigned_to_id: UUID, user_id: UUID, tenant_id: UUID
    ) -> BulkTaskOperation:
        """Bulk assign tasks to a user."""
        operation = BulkTaskOperation(
            "bulk_assign", task_ids, user_id, tenant_id, assigned_to_id=assigned_to_id
        )

        try:
            # Get tasks
            tasks = self.repository.get_tasks_by_ids(tenant_id, task_ids)

            # Assign each task
            for task in tasks:
                try:
                    old_assigned_to_id = task.assigned_to_id

                    # Update task
                    updated_task = self.repository.update_task(
                        task.id,
                        {"assigned_to_id": assigned_to_id, "updated_by_id": user_id},
                    )

                    operation.results.append(
                        {
                            "task_id": str(task.id),
                            "old_assigned_to_id": (
                                str(old_assigned_to_id) if old_assigned_to_id else None
                            ),
                            "new_assigned_to_id": str(assigned_to_id),
                            "success": True,
                        }
                    )

                    # Send notification
                    await self.notification_service.notify_task_assigned(
                        updated_task, assigned_to_id, user_id
                    )

                    # Invalidate cache
                    await self.cache_invalidation.invalidate_on_task_assign(
                        tenant_id,
                        task.id,
                        old_assigned_to_id,
                        assigned_to_id,
                        user_id,
                        task.created_by_id,
                    )

                except Exception as e:
                    logger.error(f"Failed to assign task {task.id}: {e}")
                    operation.errors.append({"task_id": str(task.id), "error": str(e)})

            # Invalidate bulk cache
            affected_users = {user_id, assigned_to_id}
            for task in tasks:
                if task.created_by_id:
                    affected_users.add(task.created_by_id)
                if task.assigned_to_id and task.assigned_to_id != assigned_to_id:
                    affected_users.add(task.assigned_to_id)

            await self.cache_invalidation.invalidate_on_bulk_operations(
                tenant_id, list(affected_users)
            )

        except Exception as e:
            logger.error(f"Bulk assign failed: {e}")
            operation.errors.append({"error": str(e)})

        return operation

    async def bulk_update_priority(
        self, task_ids: list[UUID], new_priority: str, user_id: UUID, tenant_id: UUID
    ) -> BulkTaskOperation:
        """Bulk update task priority."""
        operation = BulkTaskOperation(
            "bulk_update_priority",
            task_ids,
            user_id,
            tenant_id,
            new_priority=new_priority,
        )

        try:
            # Validate priority
            try:
                TaskPriority(new_priority)
            except ValueError:
                raise ValueError(f"Invalid priority: {new_priority}")

            # Get tasks
            tasks = self.repository.get_tasks_by_ids(tenant_id, task_ids)

            # Update each task
            for task in tasks:
                try:
                    old_priority = task.priority

                    # Update task
                    self.repository.update_task(
                        task.id, {"priority": new_priority, "updated_by_id": user_id}
                    )

                    operation.results.append(
                        {
                            "task_id": str(task.id),
                            "old_priority": old_priority,
                            "new_priority": new_priority,
                            "success": True,
                        }
                    )

                    # Invalidate cache
                    await self.cache_invalidation.invalidate_on_task_update(
                        tenant_id,
                        task.id,
                        task.assigned_to_id,
                        task.assigned_to_id,
                        task.created_by_id,
                        user_id,
                    )

                except Exception as e:
                    logger.error(f"Failed to update priority for task {task.id}: {e}")
                    operation.errors.append({"task_id": str(task.id), "error": str(e)})

            # Invalidate bulk cache
            affected_users = {user_id}
            for task in tasks:
                if task.assigned_to_id:
                    affected_users.add(task.assigned_to_id)
                if task.created_by_id:
                    affected_users.add(task.created_by_id)

            await self.cache_invalidation.invalidate_on_bulk_operations(
                tenant_id, list(affected_users)
            )

        except Exception as e:
            logger.error(f"Bulk priority update failed: {e}")
            operation.errors.append({"error": str(e)})

        return operation

    async def bulk_delete(
        self, task_ids: list[UUID], user_id: UUID, tenant_id: UUID
    ) -> BulkTaskOperation:
        """Bulk delete tasks."""
        operation = BulkTaskOperation("bulk_delete", task_ids, user_id, tenant_id)

        try:
            # Get tasks before deletion
            tasks = self.repository.get_tasks_by_ids(tenant_id, task_ids)

            # Delete each task
            for task in tasks:
                try:
                    # Store task info for notifications

                    # Delete task
                    self.repository.delete_task(task.id)

                    operation.results.append(
                        {"task_id": str(task.id), "title": task.title, "success": True}
                    )

                    # Invalidate cache
                    await self.cache_invalidation.invalidate_on_task_delete(
                        tenant_id,
                        task.id,
                        task.assigned_to_id,
                        task.created_by_id,
                        user_id,
                    )

                except Exception as e:
                    logger.error(f"Failed to delete task {task.id}: {e}")
                    operation.errors.append({"task_id": str(task.id), "error": str(e)})

            # Invalidate bulk cache
            affected_users = {user_id}
            for task in tasks:
                if task.assigned_to_id:
                    affected_users.add(task.assigned_to_id)
                if task.created_by_id:
                    affected_users.add(task.created_by_id)

            await self.cache_invalidation.invalidate_on_bulk_operations(
                tenant_id, list(affected_users)
            )

        except Exception as e:
            logger.error(f"Bulk delete failed: {e}")
            operation.errors.append({"error": str(e)})

        return operation

    async def bulk_update_due_date(
        self,
        task_ids: list[UUID],
        new_due_date: datetime | None,
        user_id: UUID,
        tenant_id: UUID,
    ) -> BulkTaskOperation:
        """Bulk update task due dates."""
        operation = BulkTaskOperation(
            "bulk_update_due_date",
            task_ids,
            user_id,
            tenant_id,
            new_due_date=new_due_date,
        )

        try:
            # Get tasks
            tasks = self.repository.get_tasks_by_ids(tenant_id, task_ids)

            # Update each task
            for task in tasks:
                try:
                    old_due_date = task.due_date

                    # Update task
                    self.repository.update_task(
                        task.id, {"due_date": new_due_date, "updated_by_id": user_id}
                    )

                    operation.results.append(
                        {
                            "task_id": str(task.id),
                            "old_due_date": (
                                old_due_date.isoformat() if old_due_date else None
                            ),
                            "new_due_date": (
                                new_due_date.isoformat() if new_due_date else None
                            ),
                            "success": True,
                        }
                    )

                    # Invalidate cache
                    await self.cache_invalidation.invalidate_on_task_update(
                        tenant_id,
                        task.id,
                        task.assigned_to_id,
                        task.assigned_to_id,
                        task.created_by_id,
                        user_id,
                    )

                except Exception as e:
                    logger.error(f"Failed to update due date for task {task.id}: {e}")
                    operation.errors.append({"task_id": str(task.id), "error": str(e)})

            # Invalidate bulk cache
            affected_users = {user_id}
            for task in tasks:
                if task.assigned_to_id:
                    affected_users.add(task.assigned_to_id)
                if task.created_by_id:
                    affected_users.add(task.created_by_id)

            await self.cache_invalidation.invalidate_on_bulk_operations(
                tenant_id, list(affected_users)
            )

        except Exception as e:
            logger.error(f"Bulk due date update failed: {e}")
            operation.errors.append({"error": str(e)})

        return operation

    def get_operation_summary(self, operation: BulkTaskOperation) -> dict:
        """Get summary of bulk operation results."""
        return {
            "operation_type": operation.operation_type,
            "total_tasks": len(operation.task_ids),
            "successful": len(operation.results),
            "failed": len(operation.errors),
            "success_rate": (
                len(operation.results) / len(operation.task_ids) * 100
                if operation.task_ids
                else 0
            ),
            "results": operation.results,
            "errors": operation.errors,
        }
