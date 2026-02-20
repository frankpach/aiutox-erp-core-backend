"""Task tags and search endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.tasks.tag_service import get_task_tag_service
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.task import TaskResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/search",
    response_model=StandardListResponse[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="Advanced task search",
    description="Search tasks with full-text and filters. Requires tasks.view permission.",
)
async def search_tasks(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
    q: str = Query("", description="Search query"),
    tag_ids: list[UUID] | None = Query(None, description="Filter by tag IDs"),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by status"
    ),
    priority: str | None = Query(None, description="Filter by priority"),
    limit: int = Query(50, description="Result limit"),
) -> StandardListResponse[TaskResponse]:
    """Advanced task search."""
    tag_service = get_task_tag_service(db)

    tasks = tag_service.search_tasks(
        tenant_id=current_user.tenant_id,
        query=q,
        tag_ids=tag_ids,
        status=status_filter,
        priority=priority,
        limit=limit,
    )

    return StandardListResponse(
        data=[TaskResponse.model_validate(task) for task in tasks],
        meta={
            "total": len(tasks),
            "page": 1,
            "page_size": len(tasks) if len(tasks) > 0 else 20,
            "total_pages": 1,
        },
        message="Search completed successfully",
    )


@router.get(
    "/tags/popular",
    response_model=StandardListResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get popular tags",
    description="Get most used tags. Requires tasks.view permission.",
)
async def get_popular_tags(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(20, description="Result limit"),
) -> StandardListResponse[dict]:
    """Get popular tags."""
    tag_service = get_task_tag_service(db)

    tags = tag_service.get_popular_tags(
        tenant_id=current_user.tenant_id,
        limit=limit,
    )

    return StandardListResponse(
        data=tags,
        meta={
            "total": len(tags),
            "page": 1,
            "page_size": len(tags) if len(tags) > 0 else 20,
            "total_pages": 1,
        },
        message="Popular tags retrieved successfully",
    )


@router.get(
    "/tags/suggest",
    response_model=StandardResponse[list[str]],
    status_code=status.HTTP_200_OK,
    summary="Suggest tags",
    description="Get tag suggestions based on search query. Requires tasks.view permission.",
)
async def suggest_tags(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, description="Result limit"),
) -> StandardResponse[list[str]]:
    """Suggest tags."""
    tag_service = get_task_tag_service(db)

    suggestions = tag_service.suggest_tags(
        tenant_id=current_user.tenant_id,
        query=q,
        limit=limit,
    )

    return StandardResponse(
        data=suggestions,
        message="Tag suggestions retrieved successfully",
    )
