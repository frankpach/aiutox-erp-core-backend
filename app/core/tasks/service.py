"""Task service for task management."""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.pubsub import EventPublisher, get_event_publisher
from app.core.pubsub.models import EventMetadata
from app.models.task import Task, TaskChecklistItem, TaskPriority, TaskStatus
from app.repositories.task_repository import TaskRepository

logger = logging.getLogger(__name__)


class TaskService:
    """Service for task management."""

    def __init__(
        self,
        db: Session,
        event_publisher: EventPublisher | None = None,
    ):
        """Initialize task service.

        Args:
            db: Database session
            event_publisher: EventPublisher instance (created if not provided)
        """
        self.db = db
        self.repository = TaskRepository(db)
        self.event_publisher = event_publisher or get_event_publisher()

    def create_task(
        self,
        title: str,
        tenant_id: UUID,
        created_by_id: UUID,
        description: str | None = None,
        status: str = TaskStatus.TODO,
        priority: str = TaskPriority.MEDIUM,
        assigned_to_id: UUID | None = None,
        due_date: datetime | None = None,
        related_entity_type: str | None = None,
        related_entity_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        """Create a new task.

        Args:
            title: Task title
            tenant_id: Tenant ID
            created_by_id: User ID who created the task
            description: Task description (optional)
            status: Task status (default: TODO)
            priority: Task priority (default: MEDIUM)
            assigned_to_id: User ID to assign task to (optional)
            due_date: Task due date (optional)
            related_entity_type: Related entity type (optional)
            related_entity_id: Related entity ID (optional)
            metadata: Additional metadata (optional)

        Returns:
            Created Task object
        """
        task = self.repository.create_task(
            {
                "tenant_id": tenant_id,
                "title": title,
                "description": description,
                "status": status,
                "priority": priority,
                "assigned_to_id": assigned_to_id,
                "created_by_id": created_by_id,
                "due_date": due_date,
                "related_entity_type": related_entity_type,
                "related_entity_id": related_entity_id,
                "metadata": metadata,
            }
        )

        # Publish event
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self.event_publisher.publish(
                        event_type="task.created",
                        entity_type="task",
                        entity_id=task.id,
                        tenant_id=tenant_id,
                        user_id=created_by_id,
                        metadata=EventMetadata(
                            source="task_service",
                            version="1.0",
                            additional_data={
                                "title": title,
                                "assigned_to_id": str(assigned_to_id) if assigned_to_id else None,
                            },
                        ),
                    )
                )
            else:
                loop.run_until_complete(
                    self.event_publisher.publish(
                        event_type="task.created",
                        entity_type="task",
                        entity_id=task.id,
                        tenant_id=tenant_id,
                        user_id=created_by_id,
                        metadata=EventMetadata(
                            source="task_service",
                            version="1.0",
                            additional_data={
                                "title": title,
                                "assigned_to_id": str(assigned_to_id) if assigned_to_id else None,
                            },
                        ),
                    )
                )
        except Exception as e:
            logger.warning(f"Failed to publish task.created event: {e}")

        logger.info(f"Task created: {task.id} ({title})")
        return task

    def get_task(self, task_id: UUID, tenant_id: UUID) -> Task | None:
        """Get a task by ID.

        Args:
            task_id: Task ID
            tenant_id: Tenant ID

        Returns:
            Task object or None if not found
        """
        return self.repository.get_task_by_id(task_id, tenant_id)

    def get_tasks(
        self,
        tenant_id: UUID,
        status: str | None = None,
        priority: str | None = None,
        assigned_to_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        """Get tasks with filters.

        Args:
            tenant_id: Tenant ID
            status: Filter by status (optional)
            priority: Filter by priority (optional)
            assigned_to_id: Filter by assigned user (optional)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Task objects
        """
        return self.repository.get_all_tasks(
            tenant_id=tenant_id,
            status=status,
            priority=priority,
            assigned_to_id=assigned_to_id,
            skip=skip,
            limit=limit,
        )

    def get_tasks_by_entity(
        self, entity_type: str, entity_id: UUID, tenant_id: UUID
    ) -> list[Task]:
        """Get tasks related to an entity.

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            tenant_id: Tenant ID

        Returns:
            List of Task objects
        """
        return self.repository.get_tasks_by_entity(entity_type, entity_id, tenant_id)

    def update_task(
        self, task_id: UUID, tenant_id: UUID, task_data: dict, user_id: UUID
    ) -> Task | None:
        """Update a task.

        Args:
            task_id: Task ID
            tenant_id: Tenant ID
            task_data: Task data to update
            user_id: User ID making the update

        Returns:
            Updated Task object or None if not found
        """
        task = self.repository.update_task(task_id, tenant_id, task_data)
        if task:
            # Publish event
            try:
                import asyncio

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        self.event_publisher.publish(
                            event_type="task.updated",
                            entity_type="task",
                            entity_id=task.id,
                            tenant_id=tenant_id,
                            user_id=user_id,
                            metadata=EventMetadata(
                                source="task_service",
                                version="1.0",
                                additional_data={"changes": list(task_data.keys())},
                            ),
                        )
                    )
                else:
                    loop.run_until_complete(
                        self.event_publisher.publish(
                            event_type="task.updated",
                            entity_type="task",
                            entity_id=task.id,
                            tenant_id=tenant_id,
                            user_id=user_id,
                            metadata=EventMetadata(
                                source="task_service",
                                version="1.0",
                                additional_data={"changes": list(task_data.keys())},
                            ),
                        )
                    )
            except Exception as e:
                logger.warning(f"Failed to publish task.updated event: {e}")

            # If status changed to DONE, set completed_at
            if "status" in task_data and task_data["status"] == TaskStatus.DONE:
                task.completed_at = datetime.now(timezone.utc)
                self.db.commit()
                self.db.refresh(task)

        return task

    def delete_task(self, task_id: UUID, tenant_id: UUID, user_id: UUID) -> bool:
        """Delete a task.

        Args:
            task_id: Task ID
            tenant_id: Tenant ID
            user_id: User ID deleting the task

        Returns:
            True if deleted successfully, False otherwise
        """
        deleted = self.repository.delete_task(task_id, tenant_id)
        if deleted:
            # Publish event
            try:
                import asyncio

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        self.event_publisher.publish(
                            event_type="task.deleted",
                            entity_type="task",
                            entity_id=task_id,
                            tenant_id=tenant_id,
                            user_id=user_id,
                            metadata=EventMetadata(
                                source="task_service",
                                version="1.0",
                                additional_data={},
                            ),
                        )
                    )
                else:
                    loop.run_until_complete(
                        self.event_publisher.publish(
                            event_type="task.deleted",
                            entity_type="task",
                            entity_id=task_id,
                            tenant_id=tenant_id,
                            user_id=user_id,
                            metadata=EventMetadata(
                                source="task_service",
                                version="1.0",
                                additional_data={},
                            ),
                        )
                    )
            except Exception as e:
                logger.warning(f"Failed to publish task.deleted event: {e}")

        return deleted

    # Checklist operations
    def add_checklist_item(
        self, task_id: UUID, tenant_id: UUID, title: str, order: int = 0
    ) -> TaskChecklistItem:
        """Add a checklist item to a task.

        Args:
            task_id: Task ID
            tenant_id: Tenant ID
            title: Checklist item title
            order: Item order (optional)

        Returns:
            Created TaskChecklistItem object
        """
        return self.repository.create_checklist_item(
            {
                "task_id": task_id,
                "tenant_id": tenant_id,
                "title": title,
                "order": order,
            }
        )

    def get_checklist_items(self, task_id: UUID, tenant_id: UUID) -> list[TaskChecklistItem]:
        """Get all checklist items for a task.

        Args:
            task_id: Task ID
            tenant_id: Tenant ID

        Returns:
            List of TaskChecklistItem objects
        """
        return self.repository.get_checklist_items(task_id, tenant_id)

    def update_checklist_item(
        self, item_id: UUID, tenant_id: UUID, item_data: dict
    ) -> TaskChecklistItem | None:
        """Update a checklist item.

        Args:
            item_id: Checklist item ID
            tenant_id: Tenant ID
            item_data: Item data to update

        Returns:
            Updated TaskChecklistItem object or None if not found
        """
        return self.repository.update_checklist_item(item_id, tenant_id, item_data)

    def delete_checklist_item(self, item_id: UUID, tenant_id: UUID) -> bool:
        """Delete a checklist item.

        Args:
            item_id: Checklist item ID
            tenant_id: Tenant ID

        Returns:
            True if deleted successfully, False otherwise
        """
        return self.repository.delete_checklist_item(item_id, tenant_id)

