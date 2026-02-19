"""Task status definitions endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.tasks.status_service import get_task_status_service
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.task_status import (
    TaskStatusCreate,
    TaskStatusResponse,
    TaskStatusUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


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
