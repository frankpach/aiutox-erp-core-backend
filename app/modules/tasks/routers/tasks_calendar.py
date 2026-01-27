"""Task calendar sync endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.tasks.task_event_sync_service import get_task_event_sync_service
from app.models.user import User
from app.schemas.common import StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter()


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
