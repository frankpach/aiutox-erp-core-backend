"""Task dependencies endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Request, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.auth.rate_limit import limiter
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.tasks.dependency_service import get_task_dependency_service
from app.core.tasks.service import TaskService
from app.models.user import User
from app.schemas.common import StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def get_task_service(db: Annotated[Session, Depends(get_db)]) -> TaskService:
    """Dependency to get TaskService."""
    return TaskService(db)


@router.get(
    "/{task_id}/dependencies",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="List task dependencies",
    description="List all dependencies and dependents for a task. Requires tasks.view permission.",
)
async def list_task_dependencies(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """List task dependencies."""
    dependency_service = get_task_dependency_service(db)

    # Verify task exists and user has access
    service = get_task_service(db)
    task = service.get_task(task_id, current_user.tenant_id)
    if not task:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TASK_NOT_FOUND",
            message=f"Task with ID {task_id} not found",
        )

    dependencies = dependency_service.get_dependencies(
        task_id=task_id, tenant_id=current_user.tenant_id
    )
    dependents = dependency_service.get_dependents(
        task_id=task_id, tenant_id=current_user.tenant_id
    )

    return StandardResponse(
        data={
            "dependencies": [
                {
                    "id": str(dep.id),
                    "task_id": str(dep.task_id),
                    "depends_on_id": str(dep.depends_on_id),
                    "dependency_type": dep.dependency_type,
                    "created_at": (
                        dep.created_at.isoformat() if dep.created_at else None
                    ),
                }
                for dep in dependencies
            ],
            "dependents": [
                {
                    "id": str(dep.id),
                    "task_id": str(dep.task_id),
                    "depends_on_id": str(dep.depends_on_id),
                    "dependency_type": dep.dependency_type,
                    "created_at": (
                        dep.created_at.isoformat() if dep.created_at else None
                    ),
                }
                for dep in dependents
            ],
        },
        message="Task dependencies retrieved successfully",
    )


@router.post(
    "/{task_id}/dependencies",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Add task dependency",
    description="Add a dependency between tasks. Requires tasks.manage permission.",
)
@limiter.limit("20/minute")
async def add_task_dependency(
    request: Request,
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    db: Annotated[Session, Depends(get_db)],
    dependency_data: dict = Body(..., description="Dependency data"),
) -> StandardResponse[dict]:
    """Add a dependency between tasks."""
    dependency_service = get_task_dependency_service(db)

    # Verify task exists and user has access
    service = get_task_service(db)
    task = service.get_task(task_id, current_user.tenant_id)
    if not task:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TASK_NOT_FOUND",
            message=f"Task with ID {task_id} not found",
        )

    depends_on_id = dependency_data.get("depends_on_id")
    dependency_type = dependency_data.get("dependency_type", "finish_to_start")

    if not depends_on_id:
        raise APIException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="depends_on_id is required",
        )

    try:
        dependency = dependency_service.add_dependency(
            task_id=task_id,
            depends_on_id=UUID(depends_on_id),
            tenant_id=current_user.tenant_id,
            dependency_type=dependency_type,
        )

        return StandardResponse(
            data={
                "id": str(dependency.id),
                "task_id": str(dependency.task_id),
                "depends_on_id": str(dependency.depends_on_id),
                "dependency_type": dependency.dependency_type,
                "created_at": (
                    dependency.created_at.isoformat() if dependency.created_at else None
                ),
            },
            message="Task dependency added successfully",
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="DEPENDENCY_ERROR",
            message=str(e),
        )


@router.delete(
    "/{task_id}/dependencies/{dependency_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove task dependency",
    description="Remove a dependency between tasks. Requires tasks.manage permission.",
)
async def remove_task_dependency(
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    dependency_id: Annotated[UUID, Path(..., description="Dependency ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Remove a task dependency."""
    dependency_service = get_task_dependency_service(db)

    # Verify task exists and user has access
    service = get_task_service(db)
    task = service.get_task(task_id, current_user.tenant_id)
    if not task:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TASK_NOT_FOUND",
            message=f"Task with ID {task_id} not found",
        )

    success = dependency_service.remove_dependency(
        dependency_id=dependency_id, tenant_id=current_user.tenant_id
    )

    if not success:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="DEPENDENCY_NOT_FOUND",
            message=f"Dependency with ID {dependency_id} not found",
        )
