"""Tasks router for task management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.config.service import ConfigService
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.tasks.comment_service import get_task_comment_service
from app.core.tasks.file_service import get_task_file_service
from app.core.tasks.service import TaskService
from app.core.tasks.status_service import get_task_status_service
from app.core.tasks.tag_service import get_task_tag_service
from app.core.tasks.task_event_sync_service import get_task_event_sync_service
from app.models.user import User
from app.schemas.common import PaginationMeta, StandardListResponse, StandardResponse
from app.schemas.task import (
    TaskAssignmentCreate,
    TaskAssignmentResponse,
    TaskChecklistItemCreate,
    TaskChecklistItemResponse,
    TaskChecklistItemUpdate,
    TaskCreate,
    TaskModuleSettings,
    TaskModuleSettingsUpdate,
    TaskResponse,
    TaskUpdate,
)
from app.schemas.task_status import (
    TaskStatusCreate,
    TaskStatusResponse,
    TaskStatusUpdate,
)

router = APIRouter()

TASK_SETTINGS_KEYS = {
    "calendar_enabled": "calendar.enabled",
    "board_enabled": "board.enabled",
    "inbox_enabled": "inbox.enabled",
    "list_enabled": "list.enabled",
    "stats_enabled": "stats.enabled",
}


def get_task_service(db: Annotated[Session, Depends(get_db)]) -> TaskService:
    """Dependency to get TaskService."""
    return TaskService(db)


def _build_task_settings(config_service: ConfigService, tenant_id: UUID) -> TaskModuleSettings:
    """Build tasks settings from config service with defaults."""
    return TaskModuleSettings(
        calendar_enabled=config_service.get(
            tenant_id, "tasks", TASK_SETTINGS_KEYS["calendar_enabled"], True
        ),
        board_enabled=config_service.get(
            tenant_id, "tasks", TASK_SETTINGS_KEYS["board_enabled"], True
        ),
        inbox_enabled=config_service.get(
            tenant_id, "tasks", TASK_SETTINGS_KEYS["inbox_enabled"], True
        ),
        list_enabled=config_service.get(
            tenant_id, "tasks", TASK_SETTINGS_KEYS["list_enabled"], True
        ),
        stats_enabled=config_service.get(
            tenant_id, "tasks", TASK_SETTINGS_KEYS["stats_enabled"], True
        ),
    )


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
    total = len(tasks)

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
        meta=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@router.get(
    "/settings",
    response_model=StandardResponse[TaskModuleSettings],
    status_code=status.HTTP_200_OK,
    summary="Get tasks settings",
    description="Get tasks module settings for the tenant. Requires tasks.view permission.",
)
async def get_task_settings(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[TaskModuleSettings]:
    """Get tasks module settings for the current tenant."""
    config_service = ConfigService(db)
    settings = _build_task_settings(config_service, current_user.tenant_id)
    return StandardResponse(
        data=settings,
        message="Tasks settings retrieved successfully",
    )


@router.put(
    "/settings",
    response_model=StandardResponse[TaskModuleSettings],
    status_code=status.HTTP_200_OK,
    summary="Update tasks settings",
    description="Update tasks module settings for the tenant. Requires tasks.manage permission.",
)
async def update_task_settings(
    settings: TaskModuleSettingsUpdate,
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[TaskModuleSettings]:
    """Update tasks module settings for the current tenant."""
    config_service = ConfigService(db)
    update_data = settings.model_dump(exclude_unset=True)
    if update_data:
        config_updates = {
            TASK_SETTINGS_KEYS[key]: value for key, value in update_data.items()
        }
        config_service.set_module_config(
            tenant_id=current_user.tenant_id,
            module="tasks",
            config_dict=config_updates,
            user_id=current_user.id,
        )

    refreshed_settings = _build_task_settings(config_service, current_user.tenant_id)
    return StandardResponse(
        data=refreshed_settings,
        message="Tasks settings updated successfully",
    )


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
    task = service.get_task(task_id, current_user.tenant_id)
    if not task:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TASK_NOT_FOUND",
            message=f"Task with ID {task_id} not found",
        )

    assignments = service.repository.get_assignments_by_task(task_id, current_user.tenant_id)

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
    task = service.get_task(task_id, current_user.tenant_id)
    if not task:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TASK_NOT_FOUND",
            message=f"Task with ID {task_id} not found",
        )

    deleted = service.repository.delete_assignment(assignment_id, current_user.tenant_id)
    if not deleted:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ASSIGNMENT_NOT_FOUND",
            message=f"Assignment with ID {assignment_id} not found",
        )


# Calendar Sync Endpoints (Sprint 1 - Fase 2)


@router.post(
    "/{task_id}/sync-calendar",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Sync task to calendar",
    description="Sync a task to calendar. Requires tasks.manage permission.",
)
async def sync_task_to_calendar(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    db: Annotated[Session, Depends(get_db)],
    calendar_provider: str = Query(default="internal", description="Calendar provider"),
    calendar_id: str | None = Query(default=None, description="Calendar ID"),
) -> StandardResponse[dict]:
    """Sync task to calendar."""
    sync_service = get_task_event_sync_service(db)

    try:
        result = await sync_service.sync_task_to_calendar(
            task_id=task_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            calendar_provider=calendar_provider,
            calendar_id=calendar_id,
        )

        return StandardResponse(
            data=result,
            message="Task synced to calendar successfully",
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="SYNC_ERROR",
            message=str(e),
        )


@router.delete(
    "/{task_id}/sync-calendar",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unsync task from calendar",
    description="Remove calendar sync for a task. Requires tasks.manage permission.",
)
async def unsync_task_from_calendar(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Unsync task from calendar."""
    sync_service = get_task_event_sync_service(db)

    success = await sync_service.unsync_task_from_calendar(
        task_id=task_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

    if not success:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TASK_NOT_FOUND",
            message=f"Task with ID {task_id} not found",
        )


@router.get(
    "/{task_id}/sync-status",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get calendar sync status",
    description="Get calendar sync status for a task. Requires tasks.view permission.",
)
async def get_calendar_sync_status(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """Get calendar sync status."""
    sync_service = get_task_event_sync_service(db)

    status_data = sync_service.get_sync_status(
        task_id=task_id,
        tenant_id=current_user.tenant_id,
    )

    return StandardResponse(
        data=status_data,
        message="Sync status retrieved successfully",
    )


@router.post(
    "/sync-batch",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Sync multiple tasks to calendar",
    description="Sync multiple tasks to calendar in batch. Requires tasks.manage permission.",
)
async def sync_batch_tasks(
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    db: Annotated[Session, Depends(get_db)],
    task_ids: list[UUID] = Query(..., description="List of task IDs"),
    calendar_provider: str = Query(default="internal", description="Calendar provider"),
    calendar_id: str | None = Query(default=None, description="Calendar ID"),
) -> StandardResponse[dict]:
    """Sync multiple tasks to calendar."""
    sync_service = get_task_event_sync_service(db)

    result = await sync_service.sync_batch_tasks(
        task_ids=task_ids,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        calendar_provider=calendar_provider,
        calendar_id=calendar_id,
    )

    return StandardResponse(
        data=result,
        message=f"Batch sync completed: {len(result['synced'])} synced, "
                f"{len(result['skipped'])} skipped, {len(result['failed'])} failed",
    )


# Task Status Endpoints (Sprint 2 - Fase 2)


@router.get(
    "/status-definitions",
    response_model=StandardListResponse[TaskStatusResponse],
    status_code=status.HTTP_200_OK,
    summary="List task status definitions",
    description="List all task status definitions for the tenant. Requires tasks.view permission.",
)
async def list_status_definitions(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardListResponse[TaskStatusResponse]:
    """List task status definitions."""
    status_service = get_task_status_service(db)
    statuses = status_service.get_statuses(current_user.tenant_id)

    return StandardListResponse(
        data=[TaskStatusResponse.model_validate(s) for s in statuses],
        meta={
            "total": len(statuses),
            "page": 1,
            "page_size": len(statuses) if len(statuses) > 0 else 20,
            "total_pages": 1,
        },
        message="Status definitions retrieved successfully",
    )


@router.post(
    "/status-definitions",
    response_model=StandardResponse[TaskStatusResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create task status definition",
    description="Create a new task status definition. Requires tasks.manage permission.",
)
async def create_status_definition(
    status_data: TaskStatusCreate,
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[TaskStatusResponse]:
    """Create task status definition."""
    status_service = get_task_status_service(db)

    new_status = status_service.create_status(
        tenant_id=current_user.tenant_id,
        name=status_data.name,
        status_type=status_data.type,
        color=status_data.color,
        order=status_data.order,
    )

    return StandardResponse(
        data=TaskStatusResponse.model_validate(new_status),
        message="Status definition created successfully",
    )


@router.put(
    "/status-definitions/{status_id}",
    response_model=StandardResponse[TaskStatusResponse],
    status_code=status.HTTP_200_OK,
    summary="Update task status definition",
    description="Update a task status definition. Cannot update system statuses. Requires tasks.manage permission.",
)
async def update_status_definition(
    status_id: Annotated[UUID, Path(..., description="Status ID")],
    status_data: TaskStatusUpdate,
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[TaskStatusResponse]:
    """Update task status definition."""
    status_service = get_task_status_service(db)

    update_dict = status_data.model_dump(exclude_unset=True)
    updated_status = status_service.update_status(
        status_id=status_id,
        tenant_id=current_user.tenant_id,
        update_data=update_dict,
    )

    if not updated_status:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="STATUS_NOT_FOUND_OR_SYSTEM",
            message=f"Status with ID {status_id} not found or is a system status",
        )

    return StandardResponse(
        data=TaskStatusResponse.model_validate(updated_status),
        message="Status definition updated successfully",
    )


@router.delete(
    "/status-definitions/{status_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task status definition",
    description="Delete a task status definition. Cannot delete system statuses or statuses in use. Requires tasks.manage permission.",
)
async def delete_status_definition(
    status_id: Annotated[UUID, Path(..., description="Status ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete task status definition."""
    status_service = get_task_status_service(db)

    deleted = status_service.delete_status(
        status_id=status_id,
        tenant_id=current_user.tenant_id,
    )

    if not deleted:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="STATUS_DELETE_ERROR",
            message="Cannot delete status: it may be a system status or in use by tasks",
        )


@router.post(
    "/status-definitions/reorder",
    response_model=StandardListResponse[TaskStatusResponse],
    status_code=status.HTTP_200_OK,
    summary="Reorder task status definitions",
    description="Reorder task status definitions. Requires tasks.manage permission.",
)
async def reorder_status_definitions(
    status_orders: dict[str, int],
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardListResponse[TaskStatusResponse]:
    """Reorder task status definitions."""
    status_service = get_task_status_service(db)

    # Convertir string keys a UUID
    status_orders_uuid = {UUID(k): v for k, v in status_orders.items()}

    statuses = status_service.reorder_statuses(
        tenant_id=current_user.tenant_id,
        status_orders=status_orders_uuid,
    )

    return StandardListResponse(
        data=[TaskStatusResponse.model_validate(s) for s in statuses],
        meta={
            "total": len(statuses),
            "page": 1,
            "page_size": len(statuses) if len(statuses) > 0 else 20,
            "total_pages": 1,
        },
        message="Status definitions reordered successfully",
    )


# Task Files Endpoints (Sprint 3 - Fase 2)


@router.post(
    "/{task_id}/files",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Attach file to task",
    description="Attach a file to a task. Requires tasks.manage permission.",
)
async def attach_file_to_task(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    db: Annotated[Session, Depends(get_db)],
    file_id: UUID = Query(..., description="File ID from files module"),
    file_name: str = Query(..., description="File name"),
    file_size: int = Query(..., description="File size in bytes"),
    file_type: str = Query(..., description="File MIME type"),
    file_url: str = Query(..., description="File URL"),
) -> StandardResponse[dict]:
    """Attach file to task."""
    file_service = get_task_file_service(db)

    try:
        attachment = file_service.attach_file(
            task_id=task_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            file_id=file_id,
            file_name=file_name,
            file_size=file_size,
            file_type=file_type,
            file_url=file_url,
        )

        return StandardResponse(
            data=attachment,
            message="File attached to task successfully",
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TASK_NOT_FOUND",
            message=str(e),
        )


@router.delete(
    "/{task_id}/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Detach file from task",
    description="Remove a file attachment from a task. Requires tasks.manage permission.",
)
async def detach_file_from_task(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    file_id: Annotated[UUID, Path(..., description="File ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Detach file from task."""
    file_service = get_task_file_service(db)

    success = file_service.detach_file(
        task_id=task_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        file_id=file_id,
    )

    if not success:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File {file_id} not found in task {task_id}",
        )


@router.get(
    "/{task_id}/files",
    response_model=StandardListResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="List task files",
    description="List all files attached to a task. Requires tasks.view permission.",
)
async def list_task_files(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardListResponse[dict]:
    """List task files."""
    file_service = get_task_file_service(db)

    files = file_service.list_files(
        task_id=task_id,
        tenant_id=current_user.tenant_id,
    )

    return StandardListResponse(
        data=files,
        meta={
            "total": len(files),
            "page": 1,
            "page_size": len(files) if len(files) > 0 else 20,
            "total_pages": 1,
        },
        message="Task files retrieved successfully",
    )


# Task Comments Endpoints (Sprint 4 - Fase 2)


@router.post(
    "/{task_id}/comments",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Add comment to task",
    description="Add a comment to a task. Supports @mentions. Requires tasks.view permission.",
)
async def add_comment_to_task(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
    content: str = Query(..., description="Comment content"),
    mentions: list[UUID] | None = Query(None, description="List of mentioned user IDs"),
) -> StandardResponse[dict]:
    """Add comment to task."""
    comment_service = get_task_comment_service(db)

    try:
        comment = comment_service.add_comment(
            task_id=task_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            content=content,
            mentions=mentions,
        )

        return StandardResponse(
            data=comment,
            message="Comment added successfully",
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TASK_NOT_FOUND",
            message=str(e),
        )


@router.put(
    "/{task_id}/comments/{comment_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Update comment",
    description="Update a comment. Only the author can update. Requires tasks.view permission.",
)
async def update_task_comment(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    comment_id: Annotated[str, Path(..., description="Comment ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
    content: str = Query(..., description="New comment content"),
) -> StandardResponse[dict]:
    """Update task comment."""
    comment_service = get_task_comment_service(db)

    comment = comment_service.update_comment(
        task_id=task_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        comment_id=comment_id,
        content=content,
    )

    if not comment:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="COMMENT_NOT_FOUND",
            message=f"Comment {comment_id} not found or you don't have permission to update it",
        )

    return StandardResponse(
        data=comment,
        message="Comment updated successfully",
    )


@router.delete(
    "/{task_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete comment",
    description="Delete a comment. Only the author can delete. Requires tasks.view permission.",
)
async def delete_task_comment(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    comment_id: Annotated[str, Path(..., description="Comment ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete task comment."""
    comment_service = get_task_comment_service(db)

    success = comment_service.delete_comment(
        task_id=task_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        comment_id=comment_id,
    )

    if not success:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="COMMENT_NOT_FOUND",
            message=f"Comment {comment_id} not found or you don't have permission to delete it",
        )


@router.get(
    "/{task_id}/comments",
    response_model=StandardListResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="List task comments",
    description="List all comments for a task. Requires tasks.view permission.",
)
async def list_task_comments(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardListResponse[dict]:
    """List task comments."""
    comment_service = get_task_comment_service(db)

    comments = comment_service.list_comments(
        task_id=task_id,
        tenant_id=current_user.tenant_id,
    )

    return StandardListResponse(
        data=comments,
        meta={
            "total": len(comments),
            "page": 1,
            "page_size": len(comments) if len(comments) > 0 else 20,
            "total_pages": 1,
        },
        message="Task comments retrieved successfully",
    )


# Task Tags & Search Endpoints (Sprint 5 - Fase 2)


@router.get(
    "/search",
    response_model=StandardListResponse[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="Advanced task search",
    description="Search tasks with full-text and filters. Requires tasks.view permission.",
)
async def search_tasks(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
    q: str = Query("", description="Search query"),
    tag_ids: list[UUID] | None = Query(None, description="Filter by tag IDs"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    priority: str | None = Query(None, description="Filter by priority"),
    limit: int = Query(50, description="Result limit"),
) -> StandardListResponse[TaskResponse]:
    """Advanced task search."""
    tag_service = get_task_tag_service(db)

    tasks = tag_service.search_tasks(
        tenant_id=current_user.tenant_id,
        query=q,
        tag_ids=tag_ids,
        status=status_filter,
        priority=priority,
        limit=limit,
    )

    return StandardListResponse(
        data=[TaskResponse.model_validate(task) for task in tasks],
        meta={
            "total": len(tasks),
            "page": 1,
            "page_size": len(tasks) if len(tasks) > 0 else 20,
            "total_pages": 1,
        },
        message="Search completed successfully",
    )


@router.get(
    "/tags/popular",
    response_model=StandardListResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get popular tags",
    description="Get most used tags. Requires tasks.view permission.",
)
async def get_popular_tags(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(20, description="Result limit"),
) -> StandardListResponse[dict]:
    """Get popular tags."""
    tag_service = get_task_tag_service(db)

    tags = tag_service.get_popular_tags(
        tenant_id=current_user.tenant_id,
        limit=limit,
    )

    return StandardListResponse(
        data=tags,
        meta={
            "total": len(tags),
            "page": 1,
            "page_size": len(tags) if len(tags) > 0 else 20,
            "total_pages": 1,
        },
        message="Popular tags retrieved successfully",
    )


@router.get(
    "/tags/suggest",
    response_model=StandardResponse[list[str]],
    status_code=status.HTTP_200_OK,
    summary="Suggest tags",
    description="Get tag suggestions based on search query. Requires tasks.view permission.",
)
async def suggest_tags(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, description="Result limit"),
) -> StandardResponse[list[str]]:
    """Suggest tags."""
    tag_service = get_task_tag_service(db)

    suggestions = tag_service.suggest_tags(
        tenant_id=current_user.tenant_id,
        query=q,
        limit=limit,
    )

    return StandardResponse(
        data=suggestions,
        message="Tag suggestions retrieved successfully",
    )


# Analytics & Preferences Endpoints (Sprint 5 - Fase 2)


@router.get(
    "/analytics/adoption",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get feature adoption metrics",
    description="Get adoption metrics for task features. Requires tasks.manage permission.",
)
async def get_adoption_metrics(
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """Get feature adoption metrics."""
    from app.analytics.task_adoption import get_task_adoption_analytics

    analytics = get_task_adoption_analytics(db)
    metrics = analytics.get_feature_adoption(current_user.tenant_id)

    return StandardResponse(
        data=metrics,
        message="Adoption metrics retrieved successfully",
    )


@router.get(
    "/analytics/trends",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get adoption trends",
    description="Get adoption trends over time. Requires tasks.manage permission.",
)
async def get_adoption_trends(
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    db: Annotated[Session, Depends(get_db)],
    days: int = Query(30, description="Days to analyze"),
) -> StandardResponse[dict]:
    """Get adoption trends."""
    from app.analytics.task_adoption import get_task_adoption_analytics

    analytics = get_task_adoption_analytics(db)
    trends = analytics.get_adoption_trends(current_user.tenant_id, days)

    return StandardResponse(
        data=trends,
        message="Adoption trends retrieved successfully",
    )


@router.get(
    "/preferences/calendar",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get user calendar preferences",
    description="Get current user's calendar preferences. Requires tasks.view permission.",
)
async def get_calendar_preferences(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """Get user calendar preferences."""
    from app.models.user_calendar_preferences import UserCalendarPreferences

    prefs = (
        db.query(UserCalendarPreferences)
        .filter(UserCalendarPreferences.user_id == current_user.id)
        .first()
    )

    if not prefs:
        # Crear preferencias por defecto
        prefs = UserCalendarPreferences(user_id=current_user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)

    return StandardResponse(
        data={
            "id": str(prefs.id),
            "user_id": str(prefs.user_id),
            "auto_sync_enabled": prefs.auto_sync_enabled,
            "default_calendar_provider": prefs.default_calendar_provider,
            "timezone": prefs.timezone,
            "time_format": prefs.time_format,
        },
        message="Calendar preferences retrieved successfully",
    )


@router.put(
    "/preferences/calendar",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Update user calendar preferences",
    description="Update current user's calendar preferences. Requires tasks.view permission.",
)
async def update_calendar_preferences(
    preferences: dict,
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """Update user calendar preferences."""
    from app.models.user_calendar_preferences import UserCalendarPreferences

    prefs = (
        db.query(UserCalendarPreferences)
        .filter(UserCalendarPreferences.user_id == current_user.id)
        .first()
    )

    if not prefs:
        prefs = UserCalendarPreferences(user_id=current_user.id)
        db.add(prefs)

    # Actualizar campos
    for key, value in preferences.items():
        if hasattr(prefs, key):
            setattr(prefs, key, value)

    db.commit()
    db.refresh(prefs)

    return StandardResponse(
        data={
            "id": str(prefs.id),
            "user_id": str(prefs.user_id),
            "auto_sync_enabled": prefs.auto_sync_enabled,
            "default_calendar_provider": prefs.default_calendar_provider,
            "timezone": prefs.timezone,
            "time_format": prefs.time_format,
        },
        message="Calendar preferences updated successfully",
    )
