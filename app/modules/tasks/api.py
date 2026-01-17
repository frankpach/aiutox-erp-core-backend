"""Tasks router for task management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.config.service import ConfigService
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.tasks.service import TaskService
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
