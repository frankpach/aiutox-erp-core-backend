"""Task core endpoints - CRUD basic operations."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.auth.rate_limit import limiter
from app.core.config.service import ConfigService
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.tasks.service import TaskService
from app.models.user import User
from app.schemas.common import PaginationMeta, StandardListResponse, StandardResponse
from app.schemas.task import (
    TaskCreate,
    TaskModuleSettings,
    TaskModuleSettingsUpdate,
    TaskResponse,
    TaskUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_task_service(db: Annotated[Session, Depends(get_db)]) -> TaskService:
    """Dependency to get TaskService."""
    return TaskService(db)

TASK_SETTINGS_KEYS = {
    "calendar_enabled": "calendar.enabled",
    "board_enabled": "board.enabled",
    "inbox_enabled": "inbox.enabled",
    "list_enabled": "list.enabled",
    "stats_enabled": "stats.enabled",
}

def _build_task_settings(config_service: ConfigService, tenant_id: UUID) -> TaskModuleSettings:
    """Build task settings from config service."""
    config = config_service.get_module_config(tenant_id, "tasks")
    return TaskModuleSettings(
        calendar_enabled=config.get("calendar.enabled", False),
        board_enabled=config.get("board.enabled", True),
        inbox_enabled=config.get("inbox.enabled", True),
        list_enabled=config.get("list.enabled", True),
        stats_enabled=config.get("stats.enabled", True),
    )


@router.post(
    "/",
    response_model=StandardResponse[TaskResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create task",
    description="Create a new task. Requires tasks.manage permission.",
)
@limiter.limit("30/minute")
async def create_task(
    request: Request,
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
    "/",
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
@limiter.limit("60/minute")
async def update_task(
    request: Request,
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
@limiter.limit("20/minute")
async def delete_task(
    request: Request,
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
