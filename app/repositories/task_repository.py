"""Task repository for data access operations."""

import json
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.task import (
    Task,
    TaskAssignment,
    TaskChecklistItem,
    TaskRecurrence,
    TaskReminder,
    Workflow,
    WorkflowExecution,
    WorkflowStep,
)

logger = logging.getLogger(__name__)


class TaskRepository:
    """Repository for task data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    # Task operations
    def create_task(self, task_data: dict) -> Task:
        """Create a new task."""
        task = Task(**task_data)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_task_by_id(self, task_id: UUID, tenant_id: UUID) -> Task | None:
        """Get task by ID and tenant."""
        return (
            self.db.query(Task)
            .filter(Task.id == task_id, Task.tenant_id == tenant_id)
            .first()
        )

    def get_task_by_id_with_checklist(self, task_id: UUID, tenant_id: UUID) -> Task | None:
        """Get task by ID and tenant with checklist items loaded."""
        from sqlalchemy.orm import joinedload

        return (
            self.db.query(Task)
            .options(joinedload(Task.checklist_items))
            .filter(Task.id == task_id, Task.tenant_id == tenant_id)
            .first()
        )

    def get_all_tasks(
        self,
        tenant_id: UUID,
        status: str | None = None,
        priority: str | None = None,
        assigned_to_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        """Get all tasks for a tenant with filters."""
        query = self.db.query(Task).filter(Task.tenant_id == tenant_id)
        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)
        if assigned_to_id:
            query = query.filter(Task.assigned_to_id == assigned_to_id)
        return query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()

    def get_tasks_with_group_visibility(
        self,
        tenant_id: UUID,
        user_id: UUID,
        user_group_ids: list[UUID],
        status: str | None = None,
        priority: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        """
        Get tasks visible to a user considering group assignments.

        A task is visible if:
        - User created it
        - User is directly assigned to it
        - User belongs to a group assigned to it

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            user_group_ids: List of group IDs the user belongs to
            status: Optional status filter
            priority: Optional priority filter
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of visible tasks
        """
        query = self.db.query(Task).filter(Task.tenant_id == tenant_id)

        # Condiciones de visibilidad
        visibility_conditions = [
            Task.created_by_id == user_id,  # Creadas por el usuario
            Task.assigned_to_id == user_id,  # Asignadas directamente
            Task.id.in_(  # Asignadas al usuario via TaskAssignment
                self.db.query(TaskAssignment.task_id).filter(
                    TaskAssignment.tenant_id == tenant_id,
                    TaskAssignment.assigned_to_id == user_id
                )
            ),
        ]

        # Si el usuario pertenece a grupos, incluir tareas asignadas a esos grupos
        if user_group_ids:
            visibility_conditions.append(
                Task.id.in_(
                    self.db.query(TaskAssignment.task_id).filter(
                        TaskAssignment.tenant_id == tenant_id,
                        TaskAssignment.assigned_to_group_id.in_(user_group_ids)
                    )
                )
            )

        query = query.filter(or_(*visibility_conditions))

        # Aplicar filtros adicionales
        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)

        return query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()

    def get_tasks_by_entity(
        self, entity_type: str, entity_id: UUID, tenant_id: UUID
    ) -> list[Task]:
        """Get tasks by related entity."""
        return (
            self.db.query(Task)
            .filter(
                Task.related_entity_type == entity_type,
                Task.related_entity_id == entity_id,
                Task.tenant_id == tenant_id,
            )
            .order_by(Task.created_at.desc())
            .all()
        )

    def update_task(self, task_id: UUID, tenant_id: UUID, task_data: dict) -> Task | None:
        """Update a task."""
        task = self.get_task_by_id(task_id, tenant_id)
        if not task:
            return None
        for key, value in task_data.items():
            setattr(task, key, value)
        self.db.commit()
        self.db.refresh(task)
        return task

    def delete_task(self, task_id: UUID, tenant_id: UUID) -> bool:
        """Delete a task."""
        task = self.get_task_by_id(task_id, tenant_id)
        if not task:
            return False
        self.db.delete(task)
        self.db.commit()
        return True

    # Checklist operations
    def create_checklist_item(self, item_data: dict) -> TaskChecklistItem:
        """Create a new checklist item."""
        item = TaskChecklistItem(**item_data)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_checklist_items(self, task_id: UUID, tenant_id: UUID) -> list[TaskChecklistItem]:
        """Get all checklist items for a task."""
        return (
            self.db.query(TaskChecklistItem)
            .filter(
                TaskChecklistItem.task_id == task_id,
                TaskChecklistItem.tenant_id == tenant_id,
            )
            .order_by(TaskChecklistItem.order)
            .all()
        )

    def update_checklist_item(
        self, item_id: UUID, tenant_id: UUID, item_data: dict
    ) -> TaskChecklistItem | None:
        """Update a checklist item."""
        item = (
            self.db.query(TaskChecklistItem)
            .filter(
                TaskChecklistItem.id == item_id,
                TaskChecklistItem.tenant_id == tenant_id,
            )
            .first()
        )
        if not item:
            return None
        for key, value in item_data.items():
            setattr(item, key, value)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_checklist_item(self, item_id: UUID, tenant_id: UUID) -> bool:
        """Delete a checklist item."""
        item = (
            self.db.query(TaskChecklistItem)
            .filter(
                TaskChecklistItem.id == item_id,
                TaskChecklistItem.tenant_id == tenant_id,
            )
            .first()
        )
        if not item:
            return False
        self.db.delete(item)
        self.db.commit()
        return True

    # TaskAssignment operations
    def create_assignment(self, assignment_data: dict, created_by_id: UUID | None = None) -> TaskAssignment:
        """Create a new task assignment with audit fields."""
        # Add audit fields
        assignment_data_with_audit = {
            **assignment_data,
            "created_by_id": created_by_id or assignment_data.get("assigned_by_id"),
            "updated_by_id": created_by_id or assignment_data.get("assigned_by_id"),
        }

        assignment = TaskAssignment(**assignment_data_with_audit)
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def get_assignments_by_task(self, task_id: UUID, tenant_id: UUID) -> list[TaskAssignment]:
        """Get all assignments for a task."""
        return (
            self.db.query(TaskAssignment)
            .filter(
                TaskAssignment.task_id == task_id,
                TaskAssignment.tenant_id == tenant_id,
            )
            .order_by(TaskAssignment.assigned_at)
            .all()
        )

    def get_assignments_by_user(self, user_id: UUID, tenant_id: UUID) -> list[TaskAssignment]:
        """Get all assignments for a user."""
        return (
            self.db.query(TaskAssignment)
            .filter(
                TaskAssignment.assigned_to_id == user_id,
                TaskAssignment.tenant_id == tenant_id,
            )
            .order_by(TaskAssignment.assigned_at.desc())
            .all()
        )

    def get_assignment_by_id(self, assignment_id: UUID, tenant_id: UUID) -> TaskAssignment | None:
        """Get assignment by ID."""
        return (
            self.db.query(TaskAssignment)
            .filter(
                TaskAssignment.id == assignment_id,
                TaskAssignment.tenant_id == tenant_id,
            )
            .first()
        )

    def delete_assignment(self, assignment_id: UUID, tenant_id: UUID) -> bool:
        """Delete an assignment."""
        assignment = self.get_assignment_by_id(assignment_id, tenant_id)
        if not assignment:
            return False
        self.db.delete(assignment)
        self.db.commit()
        return True

    def update_assignment(
        self,
        assignment_id: UUID,
        tenant_id: UUID,
        assignment_data: dict,
        updated_by_id: UUID | None = None
    ) -> TaskAssignment | None:
        """Update an assignment with audit fields."""
        assignment = self.get_assignment_by_id(assignment_id, tenant_id)
        if not assignment:
            return None

        # Add audit fields
        assignment_data_with_audit = {
            **assignment_data,
            "updated_by_id": updated_by_id,
        }

        for key, value in assignment_data_with_audit.items():
            setattr(assignment, key, value)

        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def count_tasks(
        self,
        tenant_id: UUID,
        status: str | None = None,
        priority: str | None = None,
        assigned_to_id: UUID | None = None,
    ) -> int:
        """Count tasks for a tenant with filters."""
        query = self.db.query(Task).filter(Task.tenant_id == tenant_id)
        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)
        if assigned_to_id:
            query = query.filter(Task.assigned_to_id == assigned_to_id)
        return query.count()

    def get_visible_tasks(
        self,
        tenant_id: UUID,
        user_id: UUID,
        status: str | None = None,
        priority: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        """Get tasks visible to a user according to visibility rules - Optimized version with cache."""
        from sqlalchemy import and_, or_
        from sqlalchemy.orm import aliased

        # Cache disabled temporarily to avoid asyncio issues
        # TODO: Fix async cache implementation

        # Use LEFT JOIN instead of subqueries for better performance
        task_assignment = aliased(TaskAssignment)

        # Optimized query with LEFT JOIN and DISTINCT
        query = (
            self.db.query(Task)
            .filter(Task.tenant_id == tenant_id)
            .outerjoin(
                task_assignment,
                and_(
                    task_assignment.task_id == Task.id,
                    task_assignment.tenant_id == tenant_id,
                    task_assignment.assigned_to_id == user_id,
                )
            )
            .filter(
                or_(
                    Task.created_by_id == user_id,  # Created by user
                    Task.assigned_to_id == user_id,  # Legacy direct assignment
                    task_assignment.id.isnot(None),  # Modern assignment via LEFT JOIN
                    # TODO: Add group assignments when groups module is available
                )
            )
            .distinct()  # Remove duplicates from LEFT JOIN
        )

        # Apply filters
        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)

        # Execute query and cache results
        tasks = (
            query.order_by(Task.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        # Cache disabled temporarily to avoid asyncio issues
        # TODO: Fix async cache implementation
        # try:
        #     from app.core.tasks.cache_service import task_cache_service
        #     from app.schemas.task import TaskResponse
        #
        #     # Convert to TaskResponse for caching
        #     task_responses = [TaskResponse.model_validate(task) for task in tasks]
        #
        #     loop = asyncio.new_event_loop()
        #     asyncio.set_event_loop(loop)
        #     try:
        #         loop.run_until_complete(
        #             task_cache_service.set_visible_tasks(
        #                 tenant_id, user_id, task_responses, status, priority, skip, limit
        #             )
        #         )
        #     finally:
        #         loop.close()
        # except Exception:
        #     # Cache failed, but query succeeded
        #     pass

        return tasks

    def get_visible_tasks_cached(
        self,
        tenant_id: UUID,
        user_id: UUID,
        status: str | None = None,
        priority: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        """Get visible tasks with caching support - Safe wrapper around get_visible_tasks."""
        import os

        # Feature flag para activar/desactivar cache
        enable_cache = os.getenv("ENABLE_TASKS_CACHE", "false").lower() == "true"

        if not enable_cache:
            # Cache desactivado, usar método original
            return self.get_visible_tasks(
                tenant_id=tenant_id,
                user_id=user_id,
                status=status,
                priority=priority,
                skip=skip,
                limit=limit,
            )

        # Generar cache key único
        cache_key = f"visible_tasks:{tenant_id}:{user_id}:{status or 'all'}:{priority or 'all'}:{skip}:{limit}"

        try:
            # Intentar obtener desde Redis cache
            from app.core.cache.redis_client import get_redis_client
            redis_client = get_redis_client()

            cached_data = redis_client.get(cache_key)
            if cached_data:
                # Deserializar y convertir a Task objects
                cached_tasks = json.loads(cached_data)
                tasks = [self._dict_to_task(task_dict) for task_dict in cached_tasks]
                logger.debug(f"Cache hit for {cache_key}: {len(tasks)} tasks")
                return tasks

        except Exception as e:
            # Error al leer cache, continuar con query normal
            logger.warning(f"Cache read failed for {cache_key}: {e}")

        # Ejecutar query normal
        start_time = datetime.now()
        tasks = self.get_visible_tasks(
            tenant_id=tenant_id,
            user_id=user_id,
            status=status,
            priority=priority,
            skip=skip,
            limit=limit,
        )
        query_time = (datetime.now() - start_time).total_seconds()

        # Guardar en cache si la query tomó más de 100ms
        if query_time > 0.1:
            try:
                # Serializar tasks para cache
                tasks_data = [self._task_to_dict(task) for task in tasks]
                redis_client.setex(cache_key, 300, json.dumps(tasks_data))  # 5 min TTL
                logger.debug(f"Cached {cache_key}: {len(tasks)} tasks (query took {query_time:.2f}s)")
            except Exception as e:
                # Error al guardar cache, no es crítico
                logger.warning(f"Cache write failed for {cache_key}: {e}")

        return tasks

    def _task_to_dict(self, task: Task) -> dict:
        """Convert Task model to dict for caching."""
        return {
            "id": str(task.id),
            "tenant_id": str(task.tenant_id),
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "assigned_to_id": str(task.assigned_to_id) if task.assigned_to_id else None,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_by_id": str(task.created_by_id),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }

    def _dict_to_task(self, data: dict) -> Task:
        """Convert dict back to Task model."""
        from datetime import datetime

        return Task(
            id=UUID(data["id"]),
            tenant_id=UUID(data["tenant_id"]),
            title=data["title"],
            description=data["description"],
            status=data["status"],
            priority=data["priority"],
            assigned_to_id=UUID(data["assigned_to_id"]) if data["assigned_to_id"] else None,
            due_date=datetime.fromisoformat(data["due_date"]) if data["due_date"] else None,
            created_by_id=UUID(data["created_by_id"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data["completed_at"] else None,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    def count_visible_tasks(
        self,
        tenant_id: UUID,
        user_id: UUID,
        status: str | None = None,
        priority: str | None = None,
    ) -> int:
        """Count tasks visible to a user according to visibility rules - Optimized version."""
        from sqlalchemy import and_, or_
        from sqlalchemy.orm import aliased

        # Use LEFT JOIN instead of subqueries for better performance (consistent with get_visible_tasks)
        task_assignment = aliased(TaskAssignment)

        # Optimized query with LEFT JOIN and DISTINCT
        query = (
            self.db.query(Task)
            .filter(Task.tenant_id == tenant_id)
            .outerjoin(
                task_assignment,
                and_(
                    task_assignment.task_id == Task.id,
                    task_assignment.tenant_id == tenant_id,
                    task_assignment.assigned_to_id == user_id,
                )
            )
            .filter(
                or_(
                    Task.created_by_id == user_id,  # Created by user
                    Task.assigned_to_id == user_id,  # Legacy direct assignment
                    task_assignment.id.isnot(None),  # Modern assignment via LEFT JOIN
                    # TODO: Add group assignments when groups module is available
                )
            )
            .distinct()  # Remove duplicates from LEFT JOIN
        )

        # Apply filters
        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)

        return query.count()

    # Reminder operations
    def create_reminder(
        self,
        task_id: UUID,
        tenant_id: UUID,
        reminder_type: str,
        reminder_time,
        message: str | None = None,
    ) -> TaskReminder:
        """Create a new task reminder."""
        reminder = TaskReminder(
            task_id=task_id,
            tenant_id=tenant_id,
            reminder_type=reminder_type,
            reminder_time=reminder_time,
            message=message,
            sent=False,
        )
        self.db.add(reminder)
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def get_reminders_by_task(self, task_id: UUID, tenant_id: UUID) -> list[TaskReminder]:
        """Get all reminders for a task."""
        return (
            self.db.query(TaskReminder)
            .filter(TaskReminder.task_id == task_id, TaskReminder.tenant_id == tenant_id)
            .order_by(TaskReminder.reminder_time)
            .all()
        )

    def get_reminder_by_id(self, reminder_id: UUID, tenant_id: UUID) -> TaskReminder | None:
        """Get reminder by ID and tenant."""
        return (
            self.db.query(TaskReminder)
            .filter(TaskReminder.id == reminder_id, TaskReminder.tenant_id == tenant_id)
            .first()
        )

    def update_reminder(
        self,
        reminder_id: UUID,
        tenant_id: UUID,
        reminder_type: str | None = None,
        reminder_time=None,
        message: str | None = None,
        sent: bool | None = None,
    ) -> TaskReminder | None:
        """Update a task reminder."""
        reminder = self.get_reminder_by_id(reminder_id, tenant_id)
        if not reminder:
            return None
        if reminder_type is not None:
            reminder.reminder_type = reminder_type
        if reminder_time is not None:
            reminder.reminder_time = reminder_time
        if message is not None:
            reminder.message = message
        if sent is not None:
            reminder.sent = sent
            if sent:
                from datetime import UTC, datetime
                reminder.sent_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def delete_reminder(self, reminder_id: UUID, tenant_id: UUID) -> bool:
        """Delete a task reminder."""
        reminder = self.get_reminder_by_id(reminder_id, tenant_id)
        if not reminder:
            return False
        self.db.delete(reminder)
        self.db.commit()
        return True

    def get_pending_reminders(
        self,
        tenant_id: UUID,
        user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None
    ) -> list[TaskReminder]:
        """Get pending reminders for a tenant with optional user visibility and date filters."""
        from datetime import UTC, datetime

        from sqlalchemy import or_

        query = self.db.query(TaskReminder).filter(
            TaskReminder.tenant_id == tenant_id,
            TaskReminder.sent.is_(False),
        )

        # Apply date filters
        if start_date:
            query = query.filter(TaskReminder.reminder_time >= start_date)
        if end_date:
            query = query.filter(TaskReminder.reminder_time <= end_date)
        else:
            # Default: only show future reminders
            query = query.filter(TaskReminder.reminder_time >= datetime.now(UTC))

        # Apply user visibility filter if provided
        if user_id:
            # Get visible task IDs for the user
            visible_tasks_subq = (
                self.db.query(Task.id)
                .filter(Task.tenant_id == tenant_id)
                .filter(
                    or_(
                        Task.created_by_id == user_id,
                        Task.assigned_to_id == user_id,
                    )
                )
                .subquery()
            )
            query = query.filter(TaskReminder.task_id.in_(visible_tasks_subq))

        return query.order_by(TaskReminder.reminder_time).all()

    # Recurrence operations
    def create_recurrence(
        self,
        task_id: UUID,
        tenant_id: UUID,
        frequency: str,
        interval: int = 1,
        start_date=None,
        end_date=None,
        max_occurrences: int | None = None,
        days_of_week: list[int] | None = None,
        day_of_month: int | None = None,
        custom_config: dict | None = None,
        active: bool = True,
    ) -> TaskRecurrence:
        """Create a new task recurrence."""
        recurrence = TaskRecurrence(
            task_id=task_id,
            tenant_id=tenant_id,
            frequency=frequency,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            max_occurrences=max_occurrences,
            current_occurrence=1,
            days_of_week=days_of_week,
            day_of_month=day_of_month,
            custom_config=custom_config,
            active=active,
        )
        self.db.add(recurrence)
        self.db.commit()
        self.db.refresh(recurrence)
        return recurrence

    def get_recurrence_by_task(self, task_id: UUID, tenant_id: UUID) -> TaskRecurrence | None:
        """Get recurrence for a task."""
        return (
            self.db.query(TaskRecurrence)
            .filter(TaskRecurrence.task_id == task_id, TaskRecurrence.tenant_id == tenant_id)
            .first()
        )

    def get_recurrence_by_id(self, recurrence_id: UUID, tenant_id: UUID) -> TaskRecurrence | None:
        """Get recurrence by ID and tenant."""
        return (
            self.db.query(TaskRecurrence)
            .filter(TaskRecurrence.id == recurrence_id, TaskRecurrence.tenant_id == tenant_id)
            .first()
        )

    def update_recurrence(
        self,
        recurrence_id: UUID,
        tenant_id: UUID,
        frequency: str | None = None,
        interval: int | None = None,
        start_date=None,
        end_date=None,
        max_occurrences: int | None = None,
        current_occurrence: int | None = None,
        days_of_week: list[int] | None = None,
        day_of_month: int | None = None,
        custom_config: dict | None = None,
        active: bool | None = None,
    ) -> TaskRecurrence | None:
        """Update a task recurrence."""
        recurrence = self.get_recurrence_by_id(recurrence_id, tenant_id)
        if not recurrence:
            return None
        if frequency is not None:
            recurrence.frequency = frequency
        if interval is not None:
            recurrence.interval = interval
        if start_date is not None:
            recurrence.start_date = start_date
        if end_date is not None:
            recurrence.end_date = end_date
        if max_occurrences is not None:
            recurrence.max_occurrences = max_occurrences
        if current_occurrence is not None:
            recurrence.current_occurrence = current_occurrence
        if days_of_week is not None:
            recurrence.days_of_week = days_of_week
        if day_of_month is not None:
            recurrence.day_of_month = day_of_month
        if custom_config is not None:
            recurrence.custom_config = custom_config
        if active is not None:
            recurrence.active = active
        self.db.commit()
        self.db.refresh(recurrence)
        return recurrence

    def delete_recurrence(self, recurrence_id: UUID, tenant_id: UUID) -> bool:
        """Delete a task recurrence."""
        recurrence = self.get_recurrence_by_id(recurrence_id, tenant_id)
        if not recurrence:
            return False
        self.db.delete(recurrence)
        self.db.commit()
        return True

    def get_active_recurrences(self, tenant_id: UUID) -> list[TaskRecurrence]:
        """Get all active recurrences for a tenant."""
        return (
            self.db.query(TaskRecurrence)
            .filter(
                TaskRecurrence.tenant_id == tenant_id,
                TaskRecurrence.active.is_(True),
            )
            .all()
        )

    def get_tasks_optimized(
        self,
        tenant_id: UUID,
        filters: dict | None = None,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[list[Task], int]:
        """Obtiene tareas con queries optimizados usando índices y eager loading."""
        from sqlalchemy import func
        from sqlalchemy.orm import joinedload, selectinload

        # Query base con joins optimizados
        query = (
            self.db.query(Task)
            .filter(Task.tenant_id == tenant_id)
            .options(
                # Eager loading solo de relaciones necesarias
                joinedload(Task.status_obj),
                selectinload(Task.checklist_items),
                joinedload(Task.assigned_to).load_only("id", "full_name", "email"),
            )
        )

        # Aplicar filtros con índices
        if filters:
            if "status" in filters and filters["status"]:
                query = query.filter(Task.status == filters["status"])

            if "assigned_to_id" in filters and filters["assigned_to_id"]:
                query = query.filter(Task.assigned_to_id == filters["assigned_to_id"])

            if "priority" in filters and filters["priority"]:
                query = query.filter(Task.priority == filters["priority"])

            if "search" in filters and filters["search"]:
                search_term = filters["search"]
                # Usar índices para búsqueda
                query = query.filter(
                    or_(
                        Task.title.ilike(f"%{search_term}%"),
                        Task.description.ilike(f"%{search_term}%")
                    )
                )

            if "template_id" in filters and filters["template_id"]:
                query = query.filter(Task.template_id == filters["template_id"])

            if "has_due_date" in filters and filters["has_due_date"]:
                query = query.filter(Task.due_date.isnot(None))

        # Contar con query optimizado
        from sqlalchemy import select
        count_query = select(func.count()).select_from(query.statement.alias())
        total = self.db.execute(count_query).scalar()

        # Paginación eficiente
        offset = (page - 1) * page_size
        tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(page_size).all()

        return tasks, total


class WorkflowRepository:
    """Repository for workflow data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    # Workflow operations
    def create_workflow(self, workflow_data: dict) -> Workflow:
        """Create a new workflow."""
        workflow = Workflow(**workflow_data)
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def get_workflow_by_id(self, workflow_id: UUID, tenant_id: UUID) -> Workflow | None:
        """Get workflow by ID and tenant."""
        return (
            self.db.query(Workflow)
            .filter(Workflow.id == workflow_id, Workflow.tenant_id == tenant_id)
            .first()
        )

    def get_all_workflows(
        self, tenant_id: UUID, enabled_only: bool = False, skip: int = 0, limit: int = 100
    ) -> list[Workflow]:
        """Get all workflows for a tenant."""
        query = self.db.query(Workflow).filter(Workflow.tenant_id == tenant_id)
        if enabled_only:
            query = query.filter(Workflow.enabled.is_(True))
        return query.order_by(Workflow.created_at.desc()).offset(skip).limit(limit).all()

    def update_workflow(
        self, workflow_id: UUID, tenant_id: UUID, workflow_data: dict
    ) -> Workflow | None:
        """Update a workflow."""
        workflow = self.get_workflow_by_id(workflow_id, tenant_id)
        if not workflow:
            return None
        for key, value in workflow_data.items():
            setattr(workflow, key, value)
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def delete_workflow(self, workflow_id: UUID, tenant_id: UUID) -> bool:
        """Delete a workflow."""
        workflow = self.get_workflow_by_id(workflow_id, tenant_id)
        if not workflow:
            return False
        self.db.delete(workflow)
        self.db.commit()
        return True

    # WorkflowStep operations
    def create_workflow_step(self, step_data: dict) -> WorkflowStep:
        """Create a new workflow step."""
        step = WorkflowStep(**step_data)
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def get_workflow_steps(self, workflow_id: UUID, tenant_id: UUID) -> list[WorkflowStep]:
        """Get all steps for a workflow."""
        return (
            self.db.query(WorkflowStep)
            .filter(
                WorkflowStep.workflow_id == workflow_id,
                WorkflowStep.tenant_id == tenant_id,
            )
            .order_by(WorkflowStep.order)
            .all()
        )

    # WorkflowExecution operations
    def create_execution(self, execution_data: dict) -> WorkflowExecution:
        """Create a new workflow execution."""
        execution = WorkflowExecution(**execution_data)
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def get_execution_by_id(
        self, execution_id: UUID, tenant_id: UUID
    ) -> WorkflowExecution | None:
        """Get workflow execution by ID and tenant."""
        return (
            self.db.query(WorkflowExecution)
            .filter(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.tenant_id == tenant_id,
            )
            .first()
        )

    def update_execution(
        self, execution_id: UUID, tenant_id: UUID, execution_data: dict
    ) -> WorkflowExecution | None:
        """Update a workflow execution."""
        execution = self.get_execution_by_id(execution_id, tenant_id)
        if not execution:
            return None
        for key, value in execution_data.items():
            setattr(execution, key, value)
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def get_executions(
        self,
        tenant_id: UUID,
        workflow_id: UUID | None = None,
        status: str | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[WorkflowExecution]:
        """Get workflow executions for a tenant with filters."""
        query = self.db.query(WorkflowExecution).filter(WorkflowExecution.tenant_id == tenant_id)
        if workflow_id:
            query = query.filter(WorkflowExecution.workflow_id == workflow_id)
        if status:
            query = query.filter(WorkflowExecution.status == status)
        if entity_type:
            query = query.filter(WorkflowExecution.entity_type == entity_type)
        if entity_id:
            query = query.filter(WorkflowExecution.entity_id == entity_id)
        return query.order_by(WorkflowExecution.started_at.desc()).offset(skip).limit(limit).all()

    def count_executions(
        self,
        tenant_id: UUID,
        workflow_id: UUID | None = None,
        status: str | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
    ) -> int:
        """Count workflow executions for a tenant with filters."""
        query = self.db.query(WorkflowExecution).filter(WorkflowExecution.tenant_id == tenant_id)
        if workflow_id:
            query = query.filter(WorkflowExecution.workflow_id == workflow_id)
        if status:
            query = query.filter(WorkflowExecution.status == status)
        if entity_type:
            query = query.filter(WorkflowExecution.entity_type == entity_type)
        if entity_id:
            query = query.filter(WorkflowExecution.entity_id == entity_id)
        return query.count()








