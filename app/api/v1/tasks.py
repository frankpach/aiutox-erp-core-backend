"""Tasks router for task management."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.deps import get_db, get_task_service
from app.core.exceptions import APIException
from app.core.tasks.service import TaskService
from app.core.tasks.workflow_service import WorkflowService
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.task import (
    TaskAssignmentCreate,
    TaskAssignmentResponse,
    TaskChecklistItemCreate,
    TaskChecklistItemResponse,
    TaskChecklistItemUpdate,
    TaskCreate,
    TaskReminderCreate,
    TaskReminderResponse,
    TaskRecurrenceResponse,
    TaskRecurrenceUpdate,
    TaskResponse,
    TaskUpdate,
)

router = APIRouter()


def get_task_service(db: Annotated[Session, Depends(get_db)]) -> TaskService:
    """Dependency to get TaskService."""
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
    description="Create a new task. Requires tasks.create permission.",
)
async def create_task(
    task_data: TaskCreate,
    current_user: Annotated[User, Depends(require_permission("tasks.create"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> StandardResponse[TaskResponse]:
    """Create a new task."""
    task = service.create_task(
        title=task_data.title,
        tenant_id=current_user.tenant_id,
        created_by_id=current_user.id,
        description=task_data.description,
        status=task_data.status,
        priority=task_data.priority,
        assigned_to_id=task_data.assigned_to_id,
        due_date=task_data.due_date,
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
    """List tasks."""
    skip = (page - 1) * page_size
    tasks = service.get_tasks(
        tenant_id=current_user.tenant_id,
        status=status,
        priority=priority,
        assigned_to_id=assigned_to_id,
        skip=skip,
        limit=page_size,
    )
    total = service.repository.count_tasks(
        tenant_id=current_user.tenant_id,
        status=status,
        priority=priority,
        assigned_to_id=assigned_to_id,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[TaskResponse.model_validate(t) for t in tasks],
        meta={
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
        message="Tasks retrieved successfully",
    )


@router.get(
    "/my-tasks",
    response_model=StandardListResponse[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="List my tasks",
    description="List tasks visible to current user (created by user or assigned to user). Requires tasks.view permission.",
)
async def list_my_tasks(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    service: Annotated[TaskService, Depends(get_task_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    status: str | None = Query(default=None, description="Filter by status"),
    priority: str | None = Query(default=None, description="Filter by priority"),
) -> StandardListResponse[TaskResponse]:
    """List tasks visible to current user."""
    skip = (page - 1) * page_size
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
        meta={
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
        message="My tasks retrieved successfully",
    )


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
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"[list_assignments] Fetching assignments for task_id={task_id}, tenant_id={current_user.tenant_id}")

    # Verify task exists - catch any exception if task not found
    try:
        logger.info("[list_assignments] Calling service.get_task...")
        task = service.get_task(task_id, current_user.tenant_id)
        logger.info(f"[list_assignments] service.get_task returned: {task}")
        if not task:
            logger.warning("[list_assignments] Task not found, returning empty list")
            return StandardListResponse(
                data=[],
                meta={
                    "total": 0,
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 1,
                },
                message="Task not found or no assignments",
            )
    except Exception as e:
        logger.error(f"[list_assignments] Exception in service.get_task: {e}", exc_info=True)
        # Return empty list if task not found or any error occurs
        return StandardListResponse(
            data=[],
            meta={
                "total": 0,
                "page": 1,
                "page_size": 20,
                "total_pages": 1,
            },
            message="Task not found or no assignments",
        )

    logger.info("[list_assignments] Fetching assignments from repository...")
    assignments = service.repository.get_assignments_by_task(task_id, current_user.tenant_id)
    logger.info(f"[list_assignments] Found {len(assignments)} assignments")

    return StandardListResponse(
        data=[TaskAssignmentResponse.model_validate(a) for a in assignments],
        meta={
            "total": len(assignments),
            "page": 1,
            "page_size": max(1, len(assignments)) if len(assignments) > 0 else 20,
            "total_pages": 1,
        },
        message="Assignments retrieved successfully",
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
            "remind_at": reminder_data.remind_at,
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
    update_dict = task_data.model_dump(exclude_unset=True)
    task = service.update_task(task_id, current_user.tenant_id, update_dict, current_user.id)

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
    deleted = service.delete_task(task_id, current_user.tenant_id, current_user.id)
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
            if task.due_date:
                # Apply date filters if provided
                if start_date and task.due_date < start_date:
                    continue
                if end_date and task.due_date > end_date:
                    continue

                agenda_items.append({
                    "id": str(task.id),
                    "title": task.title,
                    "date": task.due_date.isoformat(),
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
) -> StandardResponse[dict]:
    """Get available calendar sources and user preferences."""
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

    # TODO: Load user preferences from database when preferences system exists
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
) -> StandardResponse[dict]:
    """Update user calendar sources preferences."""
    # TODO: Save preferences to database when preferences system exists
    # For now, just return success

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





