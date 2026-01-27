"""Task checklist endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.auth.rate_limit import limiter
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.tasks.service import TaskService
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.task import (
    TaskChecklistItemCreate,
    TaskChecklistItemResponse,
    TaskChecklistItemUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_task_service(db: Annotated[Session, Depends(get_db)]) -> TaskService:
    """Dependency to get TaskService."""
    return TaskService(db)


@router.post(
    "/{task_id}/checklist",
    response_model=StandardResponse[TaskChecklistItemResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add checklist item",
    description="Add a checklist item to a task. Requires tasks.manage permission.",
)
@limiter.limit("30/minute")
async def add_checklist_item(
    request: Request,
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
