"""Tasks router for task management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.tasks.service import TaskService
from app.core.tasks.workflow_service import WorkflowService
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.task import (
    TaskChecklistItemCreate,
    TaskChecklistItemResponse,
    TaskChecklistItemUpdate,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    WorkflowCreate,
    WorkflowExecutionCreate,
    WorkflowExecutionResponse,
    WorkflowResponse,
    WorkflowStepCreate,
    WorkflowStepResponse,
    WorkflowUpdate,
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
    description="Create a new task. Requires tasks.manage permission.",
)
async def create_task(
    task_data: TaskCreate,
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
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
    status: str | None = Query(None, description="Filter by status"),
    priority: str | None = Query(None, description="Filter by priority"),
    assigned_to_id: UUID | None = Query(None, description="Filter by assigned user"),
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
    total = len(tasks)  # TODO: Add count method to repository

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Tasks retrieved successfully",
    )


@router.get(
    "/{task_id}",
    response_model=StandardResponse[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="Get task",
    description="Get a specific task by ID. Requires tasks.view permission.",
)
async def get_task(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> StandardResponse[TaskResponse]:
    """Get a specific task."""
    task = service.get_task(task_id, current_user.tenant_id)
    if not task:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TASK_NOT_FOUND",
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
    task_id: UUID = Path(..., description="Task ID"),
    task_data: TaskUpdate = ...,
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> StandardResponse[TaskResponse]:
    """Update a task."""
    update_dict = task_data.model_dump(exclude_unset=True)
    task = service.update_task(task_id, current_user.tenant_id, update_dict, current_user.id)

    if not task:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TASK_NOT_FOUND",
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
    task_id: UUID = Path(..., description="Task ID"),
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> None:
    """Delete a task."""
    deleted = service.delete_task(task_id, current_user.tenant_id, current_user.id)
    if not deleted:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TASK_NOT_FOUND",
            message=f"Task with ID {task_id} not found",
        )


# Checklist endpoints
@router.post(
    "/{task_id}/checklist",
    response_model=StandardResponse[TaskChecklistItemResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add checklist item",
    description="Add a checklist item to a task. Requires tasks.manage permission.",
)
async def add_checklist_item(
    task_id: UUID = Path(..., description="Task ID"),
    item_data: TaskChecklistItemCreate = ...,
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> StandardResponse[TaskChecklistItemResponse]:
    """Add a checklist item to a task."""
    # Verify task exists
    task = service.get_task(task_id, current_user.tenant_id)
    if not task:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TASK_NOT_FOUND",
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
    task_id: UUID = Path(..., description="Task ID"),
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> StandardListResponse[TaskChecklistItemResponse]:
    """List checklist items for a task."""
    items = service.get_checklist_items(task_id, current_user.tenant_id)

    return StandardListResponse(
        data=[TaskChecklistItemResponse.model_validate(i) for i in items],
        total=len(items),
        page=1,
        page_size=len(items),
        total_pages=1,
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
    item_id: UUID = Path(..., description="Checklist item ID"),
    item_data: TaskChecklistItemUpdate = ...,
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> StandardResponse[TaskChecklistItemResponse]:
    """Update a checklist item."""
    update_dict = item_data.model_dump(exclude_unset=True)
    item = service.update_checklist_item(item_id, current_user.tenant_id, update_dict)

    if not item:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="CHECKLIST_ITEM_NOT_FOUND",
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
    item_id: UUID = Path(..., description="Checklist item ID"),
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> None:
    """Delete a checklist item."""
    deleted = service.delete_checklist_item(item_id, current_user.tenant_id)
    if not deleted:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="CHECKLIST_ITEM_NOT_FOUND",
            message=f"Checklist item with ID {item_id} not found",
        )

