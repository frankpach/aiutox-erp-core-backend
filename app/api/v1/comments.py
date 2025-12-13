"""Comments router for comments and collaboration management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.comments.service import CommentService
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.models.user import User
from app.schemas.comment import (
    CommentAttachmentCreate,
    CommentAttachmentResponse,
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    CommentMentionResponse,
)
from app.schemas.common import StandardListResponse, StandardResponse

router = APIRouter()


def get_comment_service(
    db: Annotated[Session, Depends(get_db)],
) -> CommentService:
    """Dependency to get CommentService."""
    return CommentService(db)


# Comment endpoints
@router.post(
    "",
    response_model=StandardResponse[CommentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create comment",
    description="Create a new comment. Requires comments.create permission.",
)
async def create_comment(
    comment_data: CommentCreate,
    current_user: Annotated[User, Depends(require_permission("comments.create"))],
    service: Annotated[CommentService, Depends(get_comment_service)],
) -> StandardResponse[CommentResponse]:
    """Create a new comment."""
    comment = service.create_comment(
        comment_data=comment_data.model_dump(exclude_none=True),
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

    return StandardResponse(
        data=CommentResponse.model_validate(comment),
        message="Comment created successfully",
    )


@router.get(
    "",
    response_model=StandardListResponse[CommentResponse],
    status_code=status.HTTP_200_OK,
    summary="List comments",
    description="List comments for an entity. Requires comments.view permission.",
)
async def list_comments(
    entity_type: str = Query(..., description="Entity type (e.g., 'product', 'order')"),
    entity_id: UUID = Query(..., description="Entity ID"),
    include_deleted: bool = Query(False, description="Include deleted comments"),
    current_user: Annotated[User, Depends(require_permission("comments.view"))],
    service: Annotated[CommentService, Depends(get_comment_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[CommentResponse]:
    """List comments for an entity."""
    skip = (page - 1) * page_size
    comments = service.get_comments_by_entity(
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=current_user.tenant_id,
        include_deleted=include_deleted,
        skip=skip,
        limit=page_size,
    )

    total = len(comments)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[CommentResponse.model_validate(c) for c in comments],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Comments retrieved successfully",
    )


@router.get(
    "/{comment_id}",
    response_model=StandardResponse[CommentResponse],
    status_code=status.HTTP_200_OK,
    summary="Get comment",
    description="Get a specific comment by ID. Requires comments.view permission.",
)
async def get_comment(
    comment_id: UUID = Path(..., description="Comment ID"),
    current_user: Annotated[User, Depends(require_permission("comments.view"))],
    service: Annotated[CommentService, Depends(get_comment_service)],
) -> StandardResponse[CommentResponse]:
    """Get a specific comment."""
    comment = service.get_comment(comment_id, current_user.tenant_id)
    if not comment:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="COMMENT_NOT_FOUND",
            message=f"Comment with ID {comment_id} not found",
        )

    return StandardResponse(
        data=CommentResponse.model_validate(comment),
        message="Comment retrieved successfully",
    )


@router.get(
    "/{comment_id}/thread",
    response_model=StandardListResponse[CommentResponse],
    status_code=status.HTTP_200_OK,
    summary="Get comment thread",
    description="Get replies to a comment. Requires comments.view permission.",
)
async def get_comment_thread(
    comment_id: UUID = Path(..., description="Parent comment ID"),
    include_deleted: bool = Query(False, description="Include deleted comments"),
    current_user: Annotated[User, Depends(require_permission("comments.view"))],
    service: Annotated[CommentService, Depends(get_comment_service)],
) -> StandardListResponse[CommentResponse]:
    """Get comment thread (replies)."""
    replies = service.get_comment_thread(
        parent_id=comment_id,
        tenant_id=current_user.tenant_id,
        include_deleted=include_deleted,
    )

    return StandardListResponse(
        data=[CommentResponse.model_validate(r) for r in replies],
        total=len(replies),
        page=1,
        page_size=len(replies),
        total_pages=1,
        message="Comment thread retrieved successfully",
    )


@router.put(
    "/{comment_id}",
    response_model=StandardResponse[CommentResponse],
    status_code=status.HTTP_200_OK,
    summary="Update comment",
    description="Update a comment. Requires comments.edit permission.",
)
async def update_comment(
    comment_id: UUID = Path(..., description="Comment ID"),
    comment_data: CommentUpdate = ...,
    current_user: Annotated[User, Depends(require_permission("comments.edit"))],
    service: Annotated[CommentService, Depends(get_comment_service)],
) -> StandardResponse[CommentResponse]:
    """Update a comment."""
    comment = service.update_comment(
        comment_id=comment_id,
        tenant_id=current_user.tenant_id,
        comment_data=comment_data.model_dump(exclude_none=True),
    )

    if not comment:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="COMMENT_NOT_FOUND",
            message=f"Comment with ID {comment_id} not found",
        )

    return StandardResponse(
        data=CommentResponse.model_validate(comment),
        message="Comment updated successfully",
    )


@router.delete(
    "/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete comment",
    description="Delete a comment (soft delete). Requires comments.delete permission.",
)
async def delete_comment(
    comment_id: UUID = Path(..., description="Comment ID"),
    current_user: Annotated[User, Depends(require_permission("comments.delete"))],
    service: Annotated[CommentService, Depends(get_comment_service)],
) -> None:
    """Delete a comment."""
    success = service.delete_comment(comment_id, current_user.tenant_id)
    if not success:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="COMMENT_NOT_FOUND",
            message=f"Comment with ID {comment_id} not found",
        )


# Comment Attachment endpoints
@router.post(
    "/{comment_id}/attachments",
    response_model=StandardResponse[CommentAttachmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add attachment",
    description="Add an attachment to a comment. Requires comments.create permission.",
)
async def add_attachment(
    comment_id: UUID = Path(..., description="Comment ID"),
    attachment_data: CommentAttachmentCreate = ...,
    current_user: Annotated[User, Depends(require_permission("comments.create"))],
    service: Annotated[CommentService, Depends(get_comment_service)],
) -> StandardResponse[CommentAttachmentResponse]:
    """Add an attachment to a comment."""
    attachment = service.add_attachment(
        comment_id=comment_id,
        file_id=attachment_data.file_id,
        tenant_id=current_user.tenant_id,
    )

    return StandardResponse(
        data=CommentAttachmentResponse.model_validate(attachment),
        message="Attachment added successfully",
    )


@router.get(
    "/{comment_id}/attachments",
    response_model=StandardListResponse[CommentAttachmentResponse],
    status_code=status.HTTP_200_OK,
    summary="Get attachments",
    description="Get attachments for a comment. Requires comments.view permission.",
)
async def get_attachments(
    comment_id: UUID = Path(..., description="Comment ID"),
    current_user: Annotated[User, Depends(require_permission("comments.view"))],
    service: Annotated[CommentService, Depends(get_comment_service)],
) -> StandardListResponse[CommentAttachmentResponse]:
    """Get attachments for a comment."""
    attachments = service.get_attachments(comment_id, current_user.tenant_id)

    return StandardListResponse(
        data=[CommentAttachmentResponse.model_validate(a) for a in attachments],
        total=len(attachments),
        page=1,
        page_size=len(attachments),
        total_pages=1,
        message="Attachments retrieved successfully",
    )

