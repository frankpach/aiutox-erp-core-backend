"""Task service for business logic."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.cache.task_cache import get_task_cache
from app.core.logging import get_logger
from app.core.pubsub import get_event_publisher
from app.core.pubsub.event_helpers import safe_publish_event
from app.core.pubsub.models import EventMetadata
from app.core.tasks.audit_integration import get_task_audit_service
from app.core.tasks.notification_service import get_task_notification_service
from app.core.tasks.state_machine import TaskStateMachine, TaskTransitionError
from app.core.tasks.templates import get_task_template_service
from app.core.tasks.webhooks import get_task_webhook_service
from app.models.task import Task, TaskPriority, TaskStatusEnum
from app.repositories.task_repository import TaskRepository

logger = get_logger(__name__)


class TaskService:
    """Service for task management."""

    def __init__(
        self,
        db: Session,
        event_publisher: Any | None = None,
    ) -> None:
        """Initialize task service."""
        self.db = db
        self.repository = TaskRepository(db)
        self.event_publisher = event_publisher or get_event_publisher()
        self.notification_service = get_task_notification_service(db)
        self.audit_service = get_task_audit_service(db)
        self.webhook_service = get_task_webhook_service(db)
        self.template_service = get_task_template_service(db)
        self.cache = get_task_cache()

    async def create_task(
        self,
        title: str,
        tenant_id: UUID,
        created_by_id: UUID,
        description: str | None = None,
        status: str = TaskStatusEnum.TODO,
        priority: str = TaskPriority.MEDIUM,
        assigned_to_id: UUID | None = None,
        due_date: datetime | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        all_day: bool = False,
        tags: list[str] | None = None,
        tag_ids: list[UUID] | None = None,
        color_override: str | None = None,
        estimated_duration: int | None = None,
        category: str | None = None,
        related_entity_type: str | None = None,
        related_entity_id: UUID | None = None,
        source_module: str | None = None,
        source_id: UUID | None = None,
        source_context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        parent_task_id: UUID | None = None,
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
            start_at: Task start datetime (optional)
            end_at: Task end datetime (optional)
            all_day: Whether task is all day
            tags: Legacy tags list (optional)
            tag_ids: Core tag IDs (optional)
            color_override: Manual color override (optional)
            related_entity_type: Related entity type (optional)
            related_entity_id: Related entity ID (optional)
            metadata: Additional metadata (optional)
            parent_task_id: Parent task ID for subtask hierarchy (optional)

        Returns:
            Created Task object

        Raises:
            ValueError: If parent_task_id creates a cycle or exceeds max depth (3)
        """
        # Validate subtask hierarchy
        if parent_task_id:
            self._validate_subtask_hierarchy(parent_task_id, tenant_id)
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
                "start_at": start_at,
                "end_at": end_at,
                "all_day": all_day,
                "tags": tags,
                "tag_ids": [str(tag_id) for tag_id in tag_ids] if tag_ids else None,
                "color_override": color_override,
                "related_entity_type": related_entity_type,
                "related_entity_id": related_entity_id,
                "source_module": source_module,
                "source_id": source_id,
                "source_context": source_context,
                "metadata": metadata,
                "parent_task_id": parent_task_id,
            }
        )

        # Publish event
        safe_publish_event(
            event_publisher=self.event_publisher,
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

        # Publish task.assigned event if task is assigned
        if assigned_to_id:
            safe_publish_event(
                event_publisher=self.event_publisher,
                event_type="task.assigned",
                entity_type="task",
                entity_id=task.id,
                tenant_id=tenant_id,
                user_id=assigned_to_id,
                metadata=EventMetadata(
                    source="task_service",
                    version="1.0",
                    additional_data={
                        "task_id": str(task.id),
                        "task_title": title,
                        "assigned_to_id": str(assigned_to_id),
                        "assigned_by_id": str(created_by_id),
                        "due_date": due_date.isoformat() if due_date else None,
                    },
                ),
            )

        logger.info(f"Task created: {task.id} ({title})")

        # Auto-sync to calendar if enabled and task has dates
        if self._should_sync_to_calendar(task, tenant_id):
            try:
                from app.core.tasks.task_event_sync_service import TaskEventSyncService
                sync_service = TaskEventSyncService(self.db)
                await sync_service.sync_task_to_event(task)
                logger.info(f"Task {task.id} synced to calendar")
            except Exception as e:
                logger.error(f"Failed to sync task {task.id} to calendar: {e}")
                # Continue without failing task creation

        # Trigger webhooks for task.created event
        await self._trigger_webhooks("task.created", {
            "task_id": str(task.id),
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "assigned_to_id": str(task.assigned_to_id) if task.assigned_to_id else None,
            "created_by_id": str(created_by_id),
            "tenant_id": str(tenant_id),
        }, tenant_id)

        return task

    def get_task(self, task_id: UUID, tenant_id: UUID) -> Task | None:
        """Get a task by ID with checklist items loaded.

        Args:
            task_id: Task ID
            tenant_id: Tenant ID

        Returns:
            Task object with checklist items or None if not found
        """
        return self.repository.get_task_by_id_with_checklist(task_id, tenant_id)

    def _should_sync_to_calendar(self, task: Task, tenant_id: UUID) -> bool:
        """Check if task should be synced to calendar.

        Args:
            task: Task to check
            tenant_id: Tenant ID

        Returns:
            True if task should be synced
        """
        # Only sync if task has dates
        if not (task.start_at or task.due_date or task.end_at):
            return False

        # Check if user has auto-sync enabled
        try:
            from app.models.user_calendar_preferences import UserCalendarPreferences

            if task.assigned_to_id:
                prefs = self.db.query(UserCalendarPreferences).filter(
                    UserCalendarPreferences.user_id == task.assigned_to_id,
                    UserCalendarPreferences.tenant_id == tenant_id,
                    UserCalendarPreferences.auto_sync_tasks
                ).first()

                return prefs is not None
        except Exception as e:
            logger.warning(f"Failed to check calendar sync preferences: {e}")
            # Default to not syncing if we can't check preferences
            return False

        return False

    def _validate_subtask_hierarchy(
        self,
        parent_task_id: UUID,
        tenant_id: UUID,
        current_task_id: UUID | None = None,
        max_depth: int = 3,
    ) -> None:
        """Validate subtask hierarchy constraints.

        Args:
            parent_task_id: Proposed parent task ID
            tenant_id: Tenant ID
            current_task_id: Current task ID (for update, to detect cycles)
            max_depth: Maximum allowed nesting depth

        Raises:
            ValueError: If validation fails (cycle, max depth, or parent not found)
        """
        # Check parent exists and belongs to same tenant
        parent = self.repository.get_task_by_id(parent_task_id, tenant_id)
        if not parent:
            raise ValueError("Parent task not found")

        # Check for circular dependency (parent cannot be a descendant of current task)
        if current_task_id:
            if parent_task_id == current_task_id:
                raise ValueError("A task cannot be its own parent")
            # Walk up from parent to check if current_task_id is an ancestor
            visited: set[UUID] = set()
            node = parent
            while node and node.parent_task_id:
                if node.parent_task_id == current_task_id:
                    raise ValueError("Circular dependency detected in subtask hierarchy")
                if node.parent_task_id in visited:
                    break  # Already a cycle in existing data, stop
                visited.add(node.parent_task_id)
                node = self.repository.get_task_by_id(node.parent_task_id, tenant_id)

        # Check max depth: count levels up from parent
        depth = 1  # Current task will be at depth = parent_depth + 1
        node = parent
        while node and node.parent_task_id:
            depth += 1
            if depth >= max_depth:
                raise ValueError(
                    f"Maximum subtask depth ({max_depth}) exceeded"
                )
            node = self.repository.get_task_by_id(node.parent_task_id, tenant_id)

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
        # Get current task for state validation
        current_task = self.repository.get_task_by_id(task_id, tenant_id)
        if not current_task:
            return None

        if "tag_ids" in task_data:
            tag_ids = task_data.get("tag_ids")
            task_data["tag_ids"] = [str(tag_id) for tag_id in tag_ids] if tag_ids else None

        # Validate subtask hierarchy if parent_task_id is being updated
        if "parent_task_id" in task_data and task_data["parent_task_id"]:
            parent_id = task_data["parent_task_id"]
            if isinstance(parent_id, str):
                parent_id = UUID(parent_id)
            self._validate_subtask_hierarchy(parent_id, tenant_id, task_id)

        # Validate state transition if status is being updated
        def _coerce_status(value: TaskStatusEnum | str) -> TaskStatusEnum:
            return value if isinstance(value, TaskStatusEnum) else TaskStatusEnum(value)

        if "status" in task_data:
            try:
                new_status = TaskStatusEnum(task_data["status"])
                current_status = _coerce_status(current_task.status)
                logger.info(f"Attempting transition: {current_status.value} -> {new_status.value}")
                TaskStateMachine.validate_transition(current_status, new_status)
                logger.info(
                    "Valid state transition: %s -> %s",
                    current_status.value,
                    new_status.value,
                )
            except ValueError as e:
                logger.error(f"Invalid status value: {task_data['status']}")
                logger.error(f"ValueError details: {e}")
                raise ValueError(f"Invalid status: {task_data['status']}")
            except TaskTransitionError as e:
                logger.error(f"Invalid state transition: {e}")
                logger.error(f"TaskTransitionError details: {type(e).__name__}: {e}")
                raise ValueError(str(e))

        task = self.repository.update_task(task_id, tenant_id, task_data)
        if task:
            # TODO: Temporarily commented out event publishing to debug timeout
            # Publish event
            additional_data = {"changes": list(task_data.keys())}
            if "status" in task_data:
                additional_data["previous_status"] = _coerce_status(current_task.status).value
                additional_data["new_status"] = _coerce_status(task.status).value

            safe_publish_event(
                event_publisher=self.event_publisher,
                event_type="task.updated",
                entity_type="task",
                entity_id=task.id,
                tenant_id=tenant_id,
                user_id=user_id,
                metadata=EventMetadata(
                    source="task_service",
                    version="1.0",
                    additional_data=additional_data,
                ),
            )

            # If status changed to DONE, set completed_at
            if "status" in task_data and _coerce_status(task.status) == TaskStatusEnum.DONE:
                task.completed_at = datetime.now(UTC)
                self.db.commit()
                self.db.refresh(task)

            # TODO: Temporarily commented out webhooks to debug timeout
            # Trigger webhooks for task.updated event
            # await self._trigger_webhooks("task.updated", {
            #     "task_id": str(task.id),
            #     "title": task.title,
            #     "status": task.status,
            #     "priority": task.priority,
            #     "assigned_to_id": str(task.assigned_to_id) if task.assigned_to_id else None,
            #     "changes": list(task_data.keys()),
            #     "tenant_id": str(tenant_id),
            # }, tenant_id)

        return task

    async def delete_task(self, task_id: UUID, tenant_id: UUID, user_id: UUID) -> bool:
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
            from app.core.pubsub.event_helpers import safe_publish_event

            safe_publish_event(
                event_publisher=self.event_publisher,
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

            # Trigger webhooks for task.deleted event
            await self._trigger_webhooks("task.deleted", {
                "task_id": str(task_id),
                "deleted_by_id": str(user_id),
                "tenant_id": str(tenant_id),
            }, tenant_id)

        return deleted

    # Checklist operations
    def add_checklist_item(
        self, task_id: UUID, tenant_id: UUID, title: str, order: int = 0
    ) -> dict:
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

    def get_checklist_items(self, task_id: UUID, tenant_id: UUID) -> list[dict]:
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
    ) -> dict | None:
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

    async def create_task_from_template(
        self,
        template_id: str,
        tenant_id: UUID,
        created_by_id: UUID,
        overrides: dict | None = None,
    ) -> Task:
        """Create a task from a template.

        Args:
            template_id: Template ID
            tenant_id: Tenant ID
            created_by_id: User ID creating the task
            overrides: Optional overrides for template data

        Returns:
            Created Task object
        """
        # Get task data from template
        task_data = self.template_service.create_task_from_template(
            template_id=template_id,
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            overrides=overrides,
        )

        # Extract checklist items if present
        checklist_items = task_data.pop("checklist_items", None)

        # Create the task
        task = await self.create_task(
            title=task_data.get("title"),
            tenant_id=UUID(task_data.get("tenant_id")),
            created_by_id=UUID(task_data.get("created_by_id")),
            description=task_data.get("description"),
            priority=task_data.get("priority", "medium"),
            estimated_duration=task_data.get("estimated_duration"),
            tags=task_data.get("tags"),
            category=task_data.get("category"),
            assigned_to_id=UUID(task_data["assigned_to_id"]) if task_data.get("assigned_to_id") else None,
            due_date=task_data.get("due_date"),
        )

        # Add checklist items if present
        if checklist_items:
            for idx, item in enumerate(checklist_items):
                self.add_checklist_item(
                    task_id=task.id,
                    tenant_id=tenant_id,
                    title=item["title"],
                    order=idx,
                )

        logger.info(f"Task created from template {template_id}: {task.id}")
        return task

    async def _trigger_webhooks(self, event: str, data: dict, tenant_id: UUID) -> None:
        """Trigger webhooks for a task event."""
        try:
            await self.webhook_service.trigger_webhooks(event, data, tenant_id)
        except Exception:
            logger.error(f"Failed to trigger webhooks for {event}")


