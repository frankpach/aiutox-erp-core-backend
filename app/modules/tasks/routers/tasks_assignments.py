"""Task assignments endpoints."""

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
    TaskAssignmentCreate,
    TaskAssignmentResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_task_service(db: Annotated[Session, Depends(get_db)]) -> TaskService:
    """Dependency to get TaskService."""
    return TaskService(db)


@router.post(
    "/{task_id}/assignments",
    response_model=StandardResponse[TaskAssignmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Assign user or group to task",
    description="Assign a user or group to a task. Requires tasks.assign permission.",
)
@limiter.limit("20/minute")
async def create_assignment(
    request: Request,
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
