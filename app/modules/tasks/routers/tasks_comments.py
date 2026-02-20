"""Task comments endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Request, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.auth.rate_limit import limiter
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.tasks.comment_service import get_task_comment_service
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/{task_id}/comments",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Add comment to task",
    description="Add a comment to a task. Supports @mentions. Requires tasks.view permission.",
)
@limiter.limit("30/minute")
async def add_comment_to_task(
    request: Request,
    task_id: Annotated[UUID, Path(..., description="Task ID")],
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
    comment_data: dict = Body(
        ..., description="Comment data with content and mentions"
    ),
) -> StandardResponse[dict]:
    """Add comment to task."""
    logger.error(f"[POST COMMENT] Endpoint llamado con task_id={task_id}")
    comment_service = get_task_comment_service(db)

    # Extraer content y mentions del body
    content = comment_data.get("content", "").strip()
    mentions = comment_data.get("mentions", [])

    if not content:
        raise APIException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="VALIDATION_ERROR",
            message="Content field is required",
        )

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
    comment_data: dict = Body(..., description="Comment update data"),
) -> StandardResponse[dict]:
    """Update task comment."""
    comment_service = get_task_comment_service(db)

    content = comment_data.get("content")
    if not content:
        raise APIException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="VALIDATION_ERROR",
            message="Content field is required",
        )

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
    logger.info(
        "Listing comments for task: task_id=%s, user_id=%s, tenant_id=%s",
        task_id,
        current_user.id,
        current_user.tenant_id,
    )

    try:
        comment_service = get_task_comment_service(db)

        comments = comment_service.list_comments(
            task_id=task_id,
            tenant_id=current_user.tenant_id,
        )

        logger.info("Retrieved %d comments for task %s", len(comments), task_id)

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

    except Exception as e:
        logger.error("Error listing comments for task %s: %s", task_id, str(e))
        raise APIException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="COMMENTS_ERROR",
            message="Failed to retrieve task comments",
        )
