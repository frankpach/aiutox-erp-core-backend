"""Tasks router for task management."""

# Standard library imports
import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

# Third-party imports
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

# Local imports
from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException

# Comment service imports removed - comments endpoints are in app/modules/tasks/api.py
from app.core.tasks.service import TaskService
from app.core.tasks.workflow_service import WorkflowService
from app.models.user import User
from app.schemas.common import PaginationMeta, StandardListResponse, StandardResponse
from app.schemas.task import (
    TaskAssignmentCreate,
    TaskAssignmentResponse,
    TaskChecklistItemCreate,
    TaskChecklistItemResponse,
    TaskChecklistItemUpdate,
    TaskCreate,
    TaskRecurrenceCreate,
    TaskRecurrenceResponse,
    TaskRecurrenceUpdate,
    TaskReminderCreate,
    TaskReminderResponse,
    TaskResponse,
    TaskUpdate,
)

logger = logging.getLogger(__name__)


router = APIRouter()


def get_task_service(db: Annotated[Session, Depends(get_db)]) -> TaskService:
    """Dependency to get TaskService."""
    return TaskService(db)


async def get_async_task_service(db: Annotated[Session, Depends(get_db)]) -> TaskService:
    """Dependency to get TaskService for async operations."""
    return TaskService(db)


def get_workflow_service(db: Annotated[Session, Depends(get_db)]) -> WorkflowService:
    """Dependency to get WorkflowService."""
    return WorkflowService(db)


# Task endpoints
@router.post(
    "",
    response_model=StandardResponse[TaskResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create task",
    description="Create a new task. Requires tasks.manage permission.",
)
async def create_task(
    task_data: TaskCreate,
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> StandardResponse[TaskResponse]:
    """Create a new task."""
    task = await service.create_task(
        title=task_data.title,
        tenant_id=current_user.tenant_id,
        created_by_id=current_user.id,
        description=task_data.description,
        status=task_data.status,
        priority=task_data.priority,
        assigned_to_id=task_data.assigned_to_id,
        due_date=task_data.due_date,
        start_at=task_data.start_at,
        end_at=task_data.end_at,
        all_day=task_data.all_day,
        tag_ids=task_data.tag_ids,
        color_override=task_data.color_override,
        related_entity_type=task_data.related_entity_type,
        related_entity_id=task_data.related_entity_id,
        source_module=task_data.source_module,
        source_id=task_data.source_id,
        source_context=task_data.source_context,
        metadata=task_data.metadata,
    )

    return StandardResponse(
        data=TaskResponse.model_validate(task),
        message="Task created successfully",
    )


@router.get(
    "",
    response_model=StandardListResponse[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="List tasks",
    description="List tasks with optional filters. Requires tasks.view permission.",
)
async def list_tasks(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    service: Annotated[TaskService, Depends(get_task_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    status: str | None = Query(default=None, description="Filter by status"),
    priority: str | None = Query(default=None, description="Filter by priority"),
    assigned_to_id: UUID | None = Query(default=None, description="Filter by assigned user"),
) -> StandardListResponse[TaskResponse]:
    """List tasks with granular permission filtering."""
    skip = (page - 1) * page_size
    tasks = service.get_tasks(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        status=status,
        priority=priority,
        assigned_to_id=assigned_to_id,
        skip=skip,
        limit=page_size,
    )

    total = service.count_tasks(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        status=status,
        priority=priority,
        assigned_to_id=assigned_to_id,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[TaskResponse.model_validate(t) for t in tasks],
        meta=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


# Special endpoints (must come BEFORE parametrized routes)
@router.get(
    "/my-tasks",
    response_model=StandardListResponse[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="List my tasks",
    description="List tasks visible to current user (created by user or assigned to user). Requires tasks.view permission.",
)
async def list_my_tasks(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    service: Annotated[TaskService, Depends(get_async_task_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    status: str | None = Query(default=None, description="Filter by status"),
    priority: str | None = Query(default=None, description="Filter by priority"),
) -> StandardListResponse[TaskResponse]:
    """List tasks visible to current user."""
    skip = (page - 1) * page_size

    # Usar cache wrapper si está disponible
    if hasattr(service.repository, 'get_visible_tasks_cached'):
        tasks = service.repository.get_visible_tasks_cached(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            status=status,
            priority=priority,
            skip=skip,
            limit=page_size,
        )
    else:
        # Fallback al método original
        tasks = service.repository.get_visible_tasks(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            status=status,
            priority=priority,
            skip=skip,
            limit=page_size,
        )
    total = service.repository.count_visible_tasks(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        status=status,
        priority=priority,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[TaskResponse.model_validate(t) for t in tasks],
        meta=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


# Dashboard endpoints (batch operations)
@router.get(
    "/dashboard",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get tasks dashboard data",
    description="Get tasks, settings, and assignments in a single request. Requires tasks.view permission.",
)
async def get_tasks_dashboard(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    service: Annotated[TaskService, Depends(get_async_task_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    status: str | None = Query(default=None, description="Filter by status"),
    priority: str | None = Query(default=None, description="Filter by priority"),
) -> StandardResponse[dict]:
    """Get tasks dashboard data in a single batch request."""
    import asyncio

    skip = (page - 1) * page_size

    # Ejecutar todas las consultas en paralelo
    async def get_tasks_data():
        # Usar cache wrapper si está disponible
        if hasattr(service.repository, 'get_visible_tasks_cached'):
            tasks = service.repository.get_visible_tasks_cached(
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                status=status,
                priority=priority,
                skip=skip,
                limit=page_size,
            )
        else:
            tasks = service.repository.get_visible_tasks(
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                status=status,
                priority=priority,
                skip=skip,
                limit=page_size,
            )

        total = service.repository.count_visible_tasks(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            status=status,
            priority=priority,
        )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "tasks": [TaskResponse.model_validate(t) for t in tasks],
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
        }

    async def get_settings_data():
        # TODO: Implementar get_task_settings cuando esté disponible
        # Por ahora retornar configuración por defecto
        return {
            "default_view": "list",
            "available_views": ["list", "board", "calendar"],
            "filters": {
                "status": ["todo", "in_progress", "done"],
                "priority": ["low", "medium", "high", "urgent"]
            }
        }

    async def get_assignments_data():
        # Obtener IDs de las tareas para buscar asignaciones
        if hasattr(service.repository, 'get_visible_tasks_cached'):
            tasks = service.repository.get_visible_tasks_cached(
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                status=status,
                priority=priority,
                skip=0,  # Obtener todas para asignaciones
                limit=1000,
            )
        else:
            tasks = service.repository.get_visible_tasks(
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                status=status,
                priority=priority,
                skip=0,
                limit=1000,
            )

        task_ids = [task.id for task in tasks]

        # Obtener asignaciones para estas tareas
        assignments = {}
        for task_id in task_ids:
            task_assignments = service.repository.get_task_assignments(
                task_id=task_id,
                tenant_id=current_user.tenant_id
            )
            if task_assignments:
                assignments[str(task_id)] = [
                    {
                        "id": str(assign.id),
                        "assigned_to_id": str(assign.assigned_to_id),
                        "assigned_at": assign.assigned_at.isoformat(),
                    }
                    for assign in task_assignments
                ]

        return assignments

    # Ejecutar todas las consultas en paralelo
    tasks_data, settings_data, assignments_data = await asyncio.gather(
        get_tasks_data(),
        get_settings_data(),
        get_assignments_data(),
        return_exceptions=True  # No falla todo si una consulta falla
    )

    # Manejar excepciones individualmente
    dashboard_data = {}

    if isinstance(tasks_data, Exception):
        from app.core.exceptions import APIException
        raise APIException(
            message="Error fetching tasks data",
            details=str(tasks_data)
        )
    else:
        dashboard_data.update(tasks_data)

    if isinstance(settings_data, Exception):
        # Settings no es crítico, usar defaults
        dashboard_data["settings"] = {
            "default_view": "list",
            "available_views": ["list", "board", "calendar"],
            "error": str(settings_data)
        }
    else:
        dashboard_data["settings"] = settings_data

    if isinstance(assignments_data, Exception):
        # Assignments no es crítico, usar vacío
        dashboard_data["assignments"] = {}
    else:
        dashboard_data["assignments"] = assignments_data

    return StandardResponse(data=dashboard_data)


# Task sub-resource endpoints (must come before /{task_id})
# Checklist endpoints
@router.post(
    "/{task_id}/checklist",
    response_model=StandardResponse[TaskChecklistItemResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add checklist item",
    description="Add a checklist item to a task. Requires tasks.manage permission.",
)
async def add_checklist_item(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    service: Annotated[TaskService, Depends(get_task_service)],
    item_data: TaskChecklistItemCreate,
) -> StandardResponse[TaskChecklistItemResponse]:
    """Add a checklist item to a task."""
    # Verify task exists
    task = service.get_task(task_id, current_user.tenant_id)
    if not task:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TASK_NOT_FOUND",
            message=f"Task with ID {task_id} not found",
        )

    item = service.add_checklist_item(
        task_id=task_id,
        tenant_id=current_user.tenant_id,
        title=item_data.title,
        order=item_data.order,
    )

    return StandardResponse(
        data=TaskChecklistItemResponse.model_validate(item),
        message="Checklist item added successfully",
    )


@router.get(
    "/{task_id}/checklist",
    response_model=StandardListResponse[TaskChecklistItemResponse],
    status_code=status.HTTP_200_OK,
    summary="List checklist items",
    description="List checklist items for a task. Requires tasks.view permission.",
)
async def list_checklist_items(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> StandardListResponse[TaskChecklistItemResponse]:
    """List checklist items for a task."""
    items = service.get_checklist_items(task_id, current_user.tenant_id)

    return StandardListResponse(
        data=[TaskChecklistItemResponse.model_validate(i) for i in items],
        meta={
            "total": len(items),
            "page": 1,
            "page_size": max(1, len(items)) if len(items) > 0 else 20,
            "total_pages": 1,
        },
        message="Checklist items retrieved successfully",
    )


@router.put(
    "/checklist/{item_id}",
    response_model=StandardResponse[TaskChecklistItemResponse],
    status_code=status.HTTP_200_OK,
    summary="Update checklist item",
    description="Update a checklist item. Requires tasks.manage permission.",
)
async def update_checklist_item(
    item_id: Annotated[UUID, Path(..., description="Checklist item ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    service: Annotated[TaskService, Depends(get_task_service)],
    item_data: TaskChecklistItemUpdate,
) -> StandardResponse[TaskChecklistItemResponse]:
    """Update a checklist item."""
    update_dict = item_data.model_dump(exclude_unset=True)
    item = service.update_checklist_item(item_id, current_user.tenant_id, update_dict)

    if not item:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="CHECKLIST_ITEM_NOT_FOUND",
            message=f"Checklist item with ID {item_id} not found",
        )

    return StandardResponse(
        data=TaskChecklistItemResponse.model_validate(item),
        message="Checklist item updated successfully",
    )


@router.delete(
    "/checklist/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete checklist item",
    description="Delete a checklist item. Requires tasks.manage permission.",
)
async def delete_checklist_item(
    item_id: Annotated[UUID, Path(..., description="Checklist item ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> None:
    """Delete a checklist item."""
    deleted = service.delete_checklist_item(item_id, current_user.tenant_id)
    if not deleted:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="CHECKLIST_ITEM_NOT_FOUND",
            message=f"Checklist item with ID {item_id} not found",
        )


# Assignment endpoints
@router.post(
    "/{task_id}/assignments",
    response_model=StandardResponse[TaskAssignmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Assign user or group to task",
    description="Assign a user or group to a task. Requires tasks.assign permission.",
)
async def create_assignment(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    assignment_data: TaskAssignmentCreate,
    current_user: Annotated[User, Depends(require_permission("tasks.assign"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> StandardResponse[TaskAssignmentResponse]:
    """Create a task assignment."""
    # Verify task exists
    task = service.get_task(task_id, current_user.tenant_id)
    if not task:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TASK_NOT_FOUND",
            message=f"Task with ID {task_id} not found",
        )

    assignment = service.repository.create_assignment(
        {
            "task_id": task_id,
            "tenant_id": current_user.tenant_id,
            "assigned_to_id": assignment_data.assigned_to_id,
            "assigned_to_group_id": assignment_data.assigned_to_group_id,
            "assigned_by_id": current_user.id,
            "role": assignment_data.role,
            "notes": assignment_data.notes,
        }
    )

    return StandardResponse(
        data=TaskAssignmentResponse.model_validate(assignment),
        message="Assignment created successfully",
    )


@router.get(
    "/{task_id}/assignments",
    response_model=StandardListResponse[TaskAssignmentResponse],
    status_code=status.HTTP_200_OK,
    summary="List task assignments",
    description="List all assignments for a task. Requires tasks.view permission.",
)
async def list_assignments(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> StandardListResponse[TaskAssignmentResponse]:
    """List assignments for a task."""
    try:
        # Obtener asignaciones directamente sin verificar tarea primero
        # Esto evita el timeout causado por get_task
        assignments = service.repository.get_assignments_by_task(task_id, current_user.tenant_id)

        return StandardListResponse(
            data=[TaskAssignmentResponse.model_validate(a) for a in assignments],
            meta={
                "total": len(assignments),
                "page": 1,
                "page_size": max(1, len(assignments)) if len(assignments) > 0 else 20,
                "total_pages": 1,
            },
            message="Asignaciones obtenidas exitosamente",
        )
    except Exception as e:
        logger.error(f"Error fetching assignments: {e}", exc_info=True)
        # Retornar lista vacía en caso de error
        return StandardListResponse(
            data=[],
            meta={
                "total": 0,
                "page": 1,
                "page_size": 20,
                "total_pages": 1,
            },
            message="Error al obtener asignaciones",
        )


@router.delete(
    "/{task_id}/assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove assignment",
    description="Remove a user or group assignment from a task. Requires tasks.assign permission.",
)
async def remove_assignment(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    assignment_id: Annotated[UUID, Path(..., description="Assignment ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.assign"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> None:
    """Remove a task assignment."""
    deleted = service.repository.delete_assignment(assignment_id, current_user.tenant_id)
    if not deleted:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ASSIGNMENT_NOT_FOUND",
            message=f"Assignment with ID {assignment_id} not found",
        )


# Reminder endpoints
@router.post(
    "/{task_id}/reminders",
    response_model=StandardResponse[TaskReminderResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create reminder",
    description="Create a reminder for a task. Requires tasks.manage permission.",
)
async def create_reminder(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    reminder_data: TaskReminderCreate,
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> StandardResponse[TaskReminderResponse]:
    """Create a task reminder."""
    # Verify task exists
    task = service.get_task(task_id, current_user.tenant_id)
    if not task:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TASK_NOT_FOUND",
            message=f"Task with ID {task_id} not found",
        )

    reminder = service.repository.create_reminder(
        {
            "task_id": task_id,
            "tenant_id": current_user.tenant_id,
            "user_id": current_user.id,
            "reminder_type": reminder_data.reminder_type,
            "reminder_time": reminder_data.reminder_time,
            "message": reminder_data.message,
        }
    )

    return StandardResponse(
        data=TaskReminderResponse.model_validate(reminder),
        message="Reminder created successfully",
    )


@router.get(
    "/{task_id}/reminders",
    response_model=StandardListResponse[TaskReminderResponse],
    status_code=status.HTTP_200_OK,
    summary="List reminders",
    description="List all reminders for a task. Requires tasks.view permission.",
)
async def list_reminders(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> StandardListResponse[TaskReminderResponse]:
    """List reminders for a task."""
    # Verify task exists
    task = service.get_task(task_id, current_user.tenant_id)
    if not task:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TASK_NOT_FOUND",
            message=f"Task with ID {task_id} not found",
        )

    reminders = service.repository.get_reminders_by_task(task_id, current_user.tenant_id)

    return StandardListResponse(
        data=[TaskReminderResponse.model_validate(r) for r in reminders],
        meta={
            "total": len(reminders),
            "page": 1,
            "page_size": max(1, len(reminders)) if len(reminders) > 0 else 20,
            "total_pages": 1,
        },
        message="Reminders retrieved successfully",
    )


# Recurrence endpoints
@router.post(
    "/{task_id}/recurrence",
    response_model=StandardResponse[TaskRecurrenceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create recurrence",
    description="Create recurrence settings for a task. Requires tasks.manage permission.",
)
async def create_recurrence(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    recurrence_data: TaskRecurrenceCreate,
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> StandardResponse[TaskRecurrenceResponse]:
    """Create recurrence settings for a task."""
    # Verify task exists
    task = service.get_task(task_id, current_user.tenant_id)
    if not task:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TASK_NOT_FOUND",
            message=f"Task with ID {task_id} not found",
        )

    recurrence = service.repository.create_recurrence(
        {
            "task_id": task_id,
            "tenant_id": current_user.tenant_id,
            "frequency": recurrence_data.frequency,
            "interval": recurrence_data.interval,
            "start_date": recurrence_data.start_date,
            "end_date": recurrence_data.end_date,
            "days_of_week": recurrence_data.days_of_week,
            "days_of_month": recurrence_data.days_of_month,
            "active": recurrence_data.active,
        }
    )

    return StandardResponse(
        data=TaskRecurrenceResponse.model_validate(recurrence),
        message="Recurrence created successfully",
    )


@router.get(
    "/{task_id}/recurrence",
    response_model=StandardResponse[TaskRecurrenceResponse],
    status_code=status.HTTP_200_OK,
    summary="Get recurrence",
    description="Get recurrence settings for a task. Requires tasks.view permission.",
)
async def get_recurrence(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> StandardResponse[TaskRecurrenceResponse]:
    """Get recurrence settings for a task."""
    # Verify task exists
    task = service.get_task(task_id, current_user.tenant_id)
    if not task:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TASK_NOT_FOUND",
            message=f"Task with ID {task_id} not found",
        )

    recurrence = service.repository.get_recurrence_by_task(task_id, current_user.tenant_id)
    if not recurrence:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RECURRENCE_NOT_FOUND",
            message=f"Recurrence not found for task {task_id}",
        )

    return StandardResponse(
        data=TaskRecurrenceResponse.model_validate(recurrence),
        message="Recurrence retrieved successfully",
    )


@router.put(
    "/{task_id}/recurrence",
    response_model=StandardResponse[TaskRecurrenceResponse],
    status_code=status.HTTP_200_OK,
    summary="Update recurrence",
    description="Update recurrence settings for a task. Requires tasks.manage permission.",
)
async def update_recurrence(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    recurrence_data: TaskRecurrenceUpdate,
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> StandardResponse[TaskRecurrenceResponse]:
    """Update recurrence settings for a task."""
    # Verify task exists
    task = service.get_task(task_id, current_user.tenant_id)
    if not task:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TASK_NOT_FOUND",
            message=f"Task with ID {task_id} not found",
        )

    recurrence = service.repository.update_recurrence(task_id, current_user.tenant_id, recurrence_data)

    return StandardResponse(
        data=TaskRecurrenceResponse.model_validate(recurrence),
        message="Recurrence updated successfully",
    )


@router.delete(
    "/{task_id}/recurrence",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete recurrence",
    description="Delete recurrence settings for a task. Requires tasks.manage permission.",
)
async def delete_recurrence(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> None:
    """Delete recurrence settings for a task."""
    deleted = service.repository.delete_recurrence(task_id, current_user.tenant_id)
    if not deleted:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RECURRENCE_NOT_FOUND",
            message=f"Recurrence not found for task {task_id}",
        )


# Task CRUD endpoints (must come after /{task_id}/... routes)
@router.get(
    "/{task_id}",
    response_model=StandardResponse[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="Get task",
    description="Get a specific task by ID. Requires tasks.view permission.",
)
async def get_task(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> StandardResponse[TaskResponse]:
    """Get a specific task."""
    task = service.get_task(task_id, current_user.tenant_id)
    if not task:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TASK_NOT_FOUND",
            message=f"Task with ID {task_id} not found",
        )

    return StandardResponse(
        data=TaskResponse.model_validate(task),
        message="Task retrieved successfully",
    )


@router.put(
    "/{task_id}",
    response_model=StandardResponse[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="Update task",
    description="Update a task. Requires tasks.manage permission.",
)
async def update_task(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    service: Annotated[TaskService, Depends(get_task_service)],
    task_data: TaskUpdate,
) -> StandardResponse[TaskResponse]:
    """Update a task."""
    try:
        update_dict = task_data.model_dump(exclude_unset=True)
        logger.info(f"Updating task {task_id} with data: {update_dict}")
        task = service.update_task(task_id, current_user.tenant_id, update_dict, current_user.id)
        logger.info(f"Task updated successfully: {task.id if task else 'None'}")

        if not task:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="TASK_NOT_FOUND",
                message=f"Task with ID {task_id} not found",
            )

        return StandardResponse(
            data=TaskResponse.model_validate(task),
            message="Task updated successfully",
        )
    except ValueError as e:
        # Handle validation errors (like invalid state transitions)
        logger.error(f"ValueError caught in update_task: {e}")
        logger.error(f"ValueError type: {type(e).__name__}")
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_TASK_DATA",
            message=str(e),
        )
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"Unexpected error in update_task: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.exception("Full traceback:")
        raise APIException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_SERVER_ERROR",
            message="An internal server error occurred",
            details={"error": str(e)},
        )


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
    description="Delete a task. Requires tasks.manage permission.",
)
async def delete_task(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> None:
    """Delete a task."""
    deleted = await service.delete_task(task_id, current_user.tenant_id, current_user.id)
    if not deleted:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TASK_NOT_FOUND",
            message=f"Task with ID {task_id} not found",
        )


# Agenda and views endpoints
@router.get(
    "/agenda",
    response_model=StandardListResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get agenda items",
    description="Get aggregated items for calendar view (tasks, reminders, etc.). Requires tasks.agenda.view permission.",
)
async def get_agenda(
    current_user: Annotated[User, Depends(require_permission("tasks.agenda.view"))],
    service: Annotated[TaskService, Depends(get_task_service)],
    start_date: datetime | None = Query(default=None, description="Start date filter"),
    end_date: datetime | None = Query(default=None, description="End date filter"),
    sources: str | None = Query(default=None, description="Comma-separated list of sources to include"),
) -> StandardListResponse[dict]:
    """Get agenda items for calendar view."""
    # Parse sources
    source_list = sources.split(",") if sources else ["tasks", "reminders"]

    # Get user's visible tasks
    tasks = service.repository.get_visible_tasks(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        skip=0,
        limit=1000,  # Large limit for agenda view
    )

    agenda_items = []

    # Add tasks to agenda
    if "tasks" in source_list:
        for task in tasks:
            task_date = task.start_at or task.due_date
            if task_date:
                # Apply date filters if provided
                if start_date and task_date < start_date:
                    continue
                if end_date and task_date > end_date:
                    continue

                agenda_items.append({
                    "id": str(task.id),
                    "title": task.title,
                    "date": task_date.isoformat(),
                    "end_date": task.end_at.isoformat() if task.end_at else None,
                    "type": "task",
                    "status": task.status,
                    "priority": task.priority,
                    "source": "tasks",
                    "source_id": str(task.id),
                })

    # Add reminders to agenda
    if "reminders" in source_list:
        reminders = service.repository.get_pending_reminders(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
        )
        for reminder in reminders:
            agenda_items.append({
                "id": str(reminder.id),
                "title": reminder.message or f"Recordatorio para {reminder.task_id}",
                "date": reminder.reminder_time.isoformat(),
                "type": "reminder",
                "source": "reminders",
                "source_id": str(reminder.task_id),
                "task_id": str(reminder.task_id),
            })

    # Sort by date
    agenda_items.sort(key=lambda x: x["date"])

    return StandardListResponse(
        data=agenda_items,
        meta={
            "total": len(agenda_items),
            "page": 1,
            "page_size": max(1, len(agenda_items)),
            "total_pages": 1,
        },
        message="Agenda items retrieved successfully",
    )


# Calendar sources endpoints
@router.get(
    "/calendar-sources",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get calendar sources",
    description="Get available calendar sources and user's preferences. Requires tasks.agenda.view permission.",
)
async def get_calendar_sources(
    current_user: Annotated[User, Depends(require_permission("tasks.agenda.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """Get available calendar sources and user preferences."""
    from app.repositories.preference_repository import PreferenceRepository

    # Available sources (hardcoded for now, could be dynamic in future)
    available_sources = [
        {
            "id": "tasks",
            "name": "Tasks",
            "description": "Task due dates and deadlines",
            "enabled": True,
        },
        {
            "id": "reminders",
            "name": "Reminders",
            "description": "Task reminders and notifications",
            "enabled": True,
        },
        {
            "id": "workflows",
            "name": "Workflows",
            "description": "Workflow deadlines and milestones",
            "enabled": False,  # Future feature
        },
        {
            "id": "projects",
            "name": "Projects",
            "description": "Project milestones and deadlines",
            "enabled": False,  # Future feature
        },
    ]

    # Load user preferences from database
    preference_repo = PreferenceRepository(db)
    calendar_prefs = preference_repo.get_user_preference(
        current_user.id, current_user.tenant_id, "calendar", "sources"
    )

    # Default preferences if not set
    if calendar_prefs:
        user_preferences = calendar_prefs.value
    else:
        user_preferences = {
            "enabled_sources": ["tasks", "reminders"],
            "default_view": "month",
            "start_of_week": "monday",
        }

    return StandardResponse(
        data={
            "available_sources": available_sources,
            "preferences": user_preferences,
        },
        message="Calendar sources retrieved successfully",
    )


@router.put(
    "/calendar-sources",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Update calendar sources preferences",
    description="Update user's calendar sources preferences. Requires tasks.agenda.manage permission.",
)
async def update_calendar_sources(
    current_user: Annotated[User, Depends(require_permission("tasks.agenda.manage"))],
    preferences: dict,
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """Update user calendar sources preferences."""
    from app.repositories.preference_repository import PreferenceRepository

    # Save preferences to database
    preference_repo = PreferenceRepository(db)
    preference_repo.create_or_update_user_preference(
        current_user.id,
        current_user.tenant_id,
        "calendar",
        "sources",
        preferences,
    )

    return StandardResponse(
        data=preferences,
        message="Calendar sources preferences updated successfully",
    )


# Views endpoints (placeholder for future implementation)
@router.get(
    "/views",
    response_model=StandardListResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get saved views",
    description="Get user's saved task views. Requires tasks.agenda.view permission.",
)
async def get_views(
    current_user: Annotated[User, Depends(require_permission("tasks.agenda.view"))],
) -> StandardListResponse[dict]:
    """Get user's saved task views."""
    # TODO: Implement when views system is ready
    return StandardListResponse(
        data=[],
        meta={
            "total": 0,
            "page": 1,
            "page_size": 20,
            "total_pages": 1,
        },
        message="Views retrieved successfully",
    )


@router.post(
    "/views",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Create saved view",
    description="Create a new saved task view. Requires tasks.agenda.manage permission.",
)
async def create_view(
    current_user: Annotated[User, Depends(require_permission("tasks.agenda.manage"))],
    view_data: dict,
) -> StandardResponse[dict]:
    """Create a new saved task view."""
    # TODO: Implement when views system is ready
    return StandardResponse(
        data=view_data,
        message="View created successfully",
    )


def parse_ics_events(ics_content: str) -> list[dict]:
    events = []
    lines = ics_content.split("\n")
    current_event = {}
    in_event = False

    for line in lines:
        line = line.strip()

        if line.startswith("BEGIN:VEVENT"):
            in_event = True
            current_event = {}
        elif line.startswith("END:VEVENT"):
            in_event = False
            if current_event:
                events.append(current_event)
        elif in_event:
            if line.startswith("SUMMARY:"):
                current_event["summary"] = line[8:].strip()
            elif line.startswith("DESCRIPTION:"):
                current_event["description"] = line[12:].strip()
            elif line.startswith("DTSTART:"):
                current_event["dtstart"] = parse_ics_date(line[8:].strip())
            elif line.startswith("DTEND:"):
                current_event["dtend"] = parse_ics_date(line[6:].strip())

    return events


def parse_ics_date(date_str: str) -> datetime | None:
    """Parse ICS date format to datetime."""
    try:
        if len(date_str) == 8:
            return datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=UTC)
        elif len(date_str) == 15 and date_str.endswith("Z"):
            return datetime.strptime(date_str[:-1], "%Y%m%dT%H%M%S").replace(tzinfo=UTC)
        elif len(date_str) == 15:
            return datetime.strptime(date_str, "%Y%m%dT%H%M%S")
        return None
    except ValueError:
        return None


# ICS import endpoints
@router.post(
    "/import-ics",
    response_model=StandardListResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Import events from ICS file",
    description="Import calendar events from an ICS file and create tasks from them. Requires tasks.manage permission.",
)
async def import_ics(
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    service: Annotated[TaskService, Depends(get_task_service)],
    ics_content: str = Query(..., description="ICS file content"),
    create_tasks: bool = Query(default=True, description="Whether to create tasks from imported events"),
) -> StandardListResponse[dict]:
    """Import events from ICS file content."""
    events = parse_ics_events(ics_content)
    created_tasks = []

    if create_tasks:
        for event in events:
            if event.get("dtstart"):
                task = await service.create_task(
                    title=event.get("summary", "Imported Event"),
                    tenant_id=current_user.tenant_id,
                    created_by_id=current_user.id,
                    description=event.get("description"),
                    due_date=event.get("dtstart"),
                    source_module="ics_import",
                    source_context=event,
                )
                created_tasks.append({
                    "id": str(task.id),
                    "title": task.title,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                })

    return StandardListResponse(
        data=created_tasks if create_tasks else events,
        meta={
            "total": len(created_tasks if create_tasks else events),
            "page": 1,
            "page_size": len(created_tasks if create_tasks else events),
            "total_pages": 1,
        },
        message=f"Successfully imported {len(events)} events from ICS file",
    )


# Test endpoint to check if FastAPI responds
@router.get("/test-comments-debug")
async def test_comments_debug():
    """Test endpoint to debug FastAPI hanging issue."""
    logger.info("[TEST_DEBUG] Endpoint reached!")
    return {"message": "FastAPI is working!", "timestamp": str(datetime.now())}

# Minimal POST endpoint to test validation
@router.post("/test-post-minimal")
async def test_post_minimal():
    """Minimal POST endpoint without any parameters."""
    print("!!! TEST POST MINIMAL REACHED !!!")
    return {"message": "POST works!"}

# Also allow GET for testing
@router.get("/test-post-minimal")
async def test_post_minimal_get():
    """GET version for testing."""
    print("!!! TEST POST MINIMAL GET REACHED !!!")
    return {"message": "GET works!"}

# NOTA: Los endpoints de comments están en app/modules/tasks/api.py
# Este archivo (app/api/v1/tasks.py) NO está registrado en el router principal
# Solo app/modules/tasks/api.py está registrado en app/api/v1/__init__.py


# TEMPORALMENTE COMENTADO - CAUSA QUE EL BACKEND SE CUELGUE
# @router.post(
#     "/{task_id}/comments",
#     response_model=StandardResponse[dict],
#     status_code=status.HTTP_201_CREATED,
#     summary="Create task comment",
#     description="Create a new comment for a specific task. Requires tasks.manage permission.",
# )
# async def create_task_comment(
#     request: Request,
#     task_id: Annotated[UUID, Path(..., description="Task ID")],
#     current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
#     comment_service: Annotated[TaskCommentService, Depends(get_task_comment_service)],
# ) -> StandardResponse[dict]:
#     """Create a new comment for a specific task."""
#     print("=" * 80)
#     print("!!! CREATE_COMMENT ENDPOINT REACHED !!!")
#     print("=" * 80)
#     logger.info("[CREATE_COMMENT] 1. FUNCTION STARTED")
#     logger.info(f"[CREATE_COMMENT] 2. Task ID: {task_id}")
#     logger.info(f"[CREATE_COMMENT] 3. User ID: {current_user.id}")

#     # Leer body raw
#     logger.info("[CREATE_COMMENT] 4. READING RAW BODY")
#     try:
#         body_bytes = await request.body()
#         logger.info(f"[CREATE_COMMENT] 5. RAW BODY BYTES: {body_bytes}")
#         body_str = body_bytes.decode('utf-8')
#         logger.info(f"[CREATE_COMMENT] 6. RAW BODY STRING: {body_str}")
#         body_json = await request.json()
#         logger.info(f"[CREATE_COMMENT] 7. PARSED JSON: {body_json}")
#     except Exception as e:
#         logger.error(f"[CREATE_COMMENT] ERROR READING BODY: {e}")
#         raise APIException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             code="INVALID_BODY",
#             message="No se pudo leer el cuerpo de la petición",
#         )

#     # Validar y crear comentario manualmente
#     if not isinstance(body_json, dict):
#         logger.error(f"[CREATE_COMMENT] Body is not dict: {type(body_json)}")
#         raise APIException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             code="INVALID_BODY_TYPE",
#             message="El cuerpo debe ser un objeto JSON",
#         )

#     content = body_json.get("content", "").strip()
#     mentions = body_json.get("mentions", [])

#     if not content:
#         logger.error(f"[CREATE_COMMENT] Empty content: {content}")
#         raise APIException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             code="VALIDATION_ERROR",
#             message="El contenido no puede estar vacío",
#         )

#     logger.info(f"[CREATE_COMMENT] 8. Processing comment: content='{content[:50]}...', mentions={mentions}")

#     try:
#         logger.info("[CREATE_COMMENT] 9. ABOUT TO CALL SERVICE")
#         # Crear comentario usando el servicio
#         result = comment_service.add_comment(
#             task_id=task_id,
#             tenant_id=current_user.tenant_id,
#             user_id=current_user.id,
#             content=content,
#             mentions=mentions,
#         )
#         logger.info("[CREATE_COMMENT] 10. SERVICE CALL COMPLETED")

#         logger.info(f"[CREATE_COMMENT] 11. Comment created successfully: {result['id']}")

#         logger.info("[CREATE_COMMENT] 12. CREATING RESPONSE")
#         response = StandardResponse(
#             data=result,
#             message="Comentario creado exitosamente",
#             meta={"comment_id": result["id"]},
#         )
#         logger.info("[CREATE_COMMENT] 13. RETURNING RESPONSE")
#         return response

#     except Exception as e:
#         logger.error(f"[CREATE_COMMENT] 14. ERROR: {e}", exc_info=True)
#         raise APIException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             code="COMMENT_CREATION_ERROR",
#             message="Error al crear el comentario",
#         )


# Endpoints de comments eliminados - están en app/modules/tasks/api.py


# Template endpoints
@router.get(
    "/templates",
    response_model=StandardListResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="List task templates",
    description="Get available task templates for QuickAdd.",
)
async def list_task_templates(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    category: str | None = Query(default=None, description="Filter by category"),
    tags: str | None = Query(default=None, description="Filter by tags (comma-separated)"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of templates"),
) -> StandardListResponse[dict]:
    """List task templates."""
    from app.core.tasks.templates import get_task_template_service

    template_service = get_task_template_service(current_user.db)

    # Parse tags
    tag_list = None
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]

    templates = template_service.get_templates(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        category=category,
        tags=tag_list,
        include_public=True
    )

    # Apply limit
    templates = templates[:limit]

    return StandardListResponse(
        data=[template.to_dict() for template in templates],
        meta=PaginationMeta(
            total=len(templates),
            page=1,
            page_size=limit,
            total_pages=1,
        ),
    )


@router.get(
    "/templates/categories",
    response_model=StandardListResponse[str],
    status_code=status.HTTP_200_OK,
    summary="List template categories",
    description="Get available template categories.",
)
async def list_template_categories(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
) -> StandardListResponse[str]:
    """List template categories."""
    from app.core.tasks.templates import get_task_template_service

    template_service = get_task_template_service(current_user.db)
    categories = template_service.get_template_categories(current_user.tenant_id)

    return StandardListResponse(
        data=categories,
        meta=PaginationMeta(
            total=len(categories),
            page=1,
            page_size=50,
            total_pages=1,
        ),
    )


@router.post(
    "/templates/{template_id}/create-task",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Create task from template",
    description="Create a new task using a template. Requires tasks.manage permission.",
)
async def create_task_from_template(
    template_id: str,
    task_overrides: dict,
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> StandardResponse[dict]:
    """Create task from template."""
    from app.core.tasks.templates import get_task_template_service

    template_service = get_task_template_service(current_user.db)

    try:
        # Get task data from template
        task_data = template_service.create_task_from_template(
            template_id=template_id,
            tenant_id=current_user.tenant_id,
            created_by_id=current_user.id,
            overrides=task_overrides
        )

        # Create the task
        task = await service.create_task(
            title=task_data["title"],
            tenant_id=current_user.tenant_id,
            created_by_id=current_user.id,
            description=task_data.get("description"),
            priority=task_data.get("priority", "medium"),
            assigned_to_id=task_data.get("assigned_to_id"),
            due_date=task_data.get("due_date"),
            tags=task_data.get("tags"),
            estimated_duration=task_data.get("estimated_duration"),
            category=task_data.get("category"),
        )

        # Add checklist items if they exist
        if "checklist_items" in task_data:
            for item_data in task_data["checklist_items"]:
                service.add_checklist_item(
                    task_id=task.id,
                    tenant_id=current_user.tenant_id,
                    title=item_data["title"],
                    order=item_data.get("order", 0)
                )

        return StandardResponse.create(
            data=task.to_dict(),
            message="Task created from template successfully",
        )

    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=str(e),
        )


@router.post(
    "/templates",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Create task template",
    description="Create a new task template.",
)
async def create_task_template(
    template_data: dict,
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
) -> StandardResponse[dict]:
    """Create task template."""
    from app.core.tasks.templates import get_task_template_service

    template_service = get_task_template_service(current_user.db)

    template = template_service.create_template(
        title=template_data["title"],
        description=template_data["description"],
        tenant_id=current_user.tenant_id,
        created_by_id=current_user.id,
        priority=template_data.get("priority", "medium"),
        estimated_duration=template_data.get("estimated_duration", 30),
        checklist_items=template_data.get("checklist_items"),
        tags=template_data.get("tags"),
        category=template_data.get("category"),
        is_public=template_data.get("is_public", False),
    )

    return StandardResponse.create(
        data=template.to_dict(),
        message="Template created successfully",
    )


@router.get(
    "/templates/popular",
    response_model=StandardListResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get popular templates",
    description="Get most used task templates.",
)
async def get_popular_templates(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    limit: int = Query(default=5, ge=1, le=20, description="Number of templates to return"),
) -> StandardListResponse[dict]:
    """Get popular templates."""
    from app.core.tasks.templates import get_task_template_service

    template_service = get_task_template_service(current_user.db)
    templates = template_service.get_popular_templates(
        tenant_id=current_user.tenant_id,
        limit=limit
    )

    return StandardListResponse(
        data=[template.to_dict() for template in templates],
        meta=PaginationMeta(
            total=len(templates),
            page=1,
            page_size=limit,
            total_pages=1,
        ),
    )



 
 @ r o u t e r . p o s t ( 
         " / { t a s k _ i d } / s y n c - t o - c a l e n d a r " , 
         r e s p o n s e _ m o d e l = S t a n d a r d R e s p o n s e [ d i c t ] , 
         s t a t u s _ c o d e = s t a t u s . H T T P _ 2 0 0 _ O K , 
         s u m m a r y = " S y n c   t a s k   t o   c a l e n d a r " , 
         d e s c r i p t i o n = " S y n c h r o n i z e   a   t a s k   w i t h   c a l e n d a r   a s   a n   e v e n t .   R e q u i r e s   t a s k s . m a n a g e   p e r m i s s i o n . " , 
 ) 
 a s y n c   d e f   s y n c _ t a s k _ t o _ c a l e n d a r ( 
         t a s k _ i d :   A n n o t a t e d [ U U I D ,   P a t h ( . . . ,   d e s c r i p t i o n = " T a s k   I D " ) ] , 
         c u r r e n t _ u s e r :   A n n o t a t e d [ U s e r ,   D e p e n d s ( r e q u i r e _ p e r m i s s i o n ( " t a s k s . m a n a g e " ) ) ] , 
         d b :   A n n o t a t e d [ S e s s i o n ,   D e p e n d s ( g e t _ d b ) ] , 
 )   - >   S t a n d a r d R e s p o n s e [ d i c t ] : 
         " " " S i n c r o n i z a r   t a r e a   c o n   c a l e n d a r i o   a u t o m � t i c a m e n t e . " " " 
         f r o m   a p p . c o r e . t a s k s . t a s k _ e v e n t _ s y n c _ s e r v i c e   i m p o r t   T a s k E v e n t S y n c S e r v i c e 
         
         s y n c _ s e r v i c e   =   T a s k E v e n t S y n c S e r v i c e ( d b ) 
         r e s u l t   =   a w a i t   s y n c _ s e r v i c e . s y n c _ t a s k _ t o _ c a l e n d a r ( 
                 t a s k _ i d = t a s k _ i d , 
                 t e n a n t _ i d = c u r r e n t _ u s e r . t e n a n t _ i d , 
                 u s e r _ i d = c u r r e n t _ u s e r . i d 
         ) 
         
         r e t u r n   S t a n d a r d R e s p o n s e ( 
                 d a t a = r e s u l t , 
                 m e s s a g e = " T a s k   s y n c h r o n i z e d   t o   c a l e n d a r   s u c c e s s f u l l y " 
         ) 
  
 