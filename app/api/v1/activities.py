"""Activities router for timeline management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.activities.service import ActivityService
from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.models.user import User
from app.schemas.activity import ActivityCreate, ActivityResponse, ActivityUpdate
from app.schemas.common import StandardListResponse, StandardResponse

router = APIRouter()


def get_activity_service(
    db: Annotated[Session, Depends(get_db)],
) -> ActivityService:
    """Dependency to get ActivityService."""
    return ActivityService(db)


@router.post(
    "",
    response_model=StandardResponse[ActivityResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create activity",
    description="Create a new activity. Requires activities.manage permission.",
)
async def create_activity(
    activity_data: ActivityCreate,
    current_user: Annotated[User, Depends(require_permission("activities.manage"))],
    service: Annotated[ActivityService, Depends(get_activity_service)],
) -> StandardResponse[ActivityResponse]:
    """Create a new activity."""
    activity = service.create_activity(
        entity_type=activity_data.entity_type,
        entity_id=activity_data.entity_id,
        activity_type=activity_data.activity_type,
        title=activity_data.title,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        description=activity_data.description,
        metadata=activity_data.metadata,
    )

    return StandardResponse(
        data=ActivityResponse.model_validate(activity),
        message="Activity created successfully",
    )


@router.get(
    "",
    response_model=StandardListResponse[ActivityResponse],
    status_code=status.HTTP_200_OK,
    summary="List activities",
    description="List activities with optional filters. Requires activities.view permission.",
)
async def list_activities(
    current_user: Annotated[User, Depends(require_permission("activities.view"))],
    service: Annotated[ActivityService, Depends(get_activity_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    activity_type: str | None = Query(None, description="Filter by activity type"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: UUID | None = Query(None, description="Filter by entity ID"),
    search: str | None = Query(None, description="Search in title and description"),
) -> StandardListResponse[ActivityResponse]:
    """List activities."""
    skip = (page - 1) * page_size

    if search:
        activities = service.search_activities(
            tenant_id=current_user.tenant_id,
            query=search,
            entity_type=entity_type,
            activity_type=activity_type,
            skip=skip,
            limit=page_size,
        )
        total = service.count_search_activities(
            tenant_id=current_user.tenant_id,
            query_text=search,
            entity_type=entity_type,
            activity_type=activity_type,
        )
    elif entity_type and entity_id:
        activities = service.get_activities(
            entity_type=entity_type,
            entity_id=entity_id,
            tenant_id=current_user.tenant_id,
            activity_type=activity_type,
            skip=skip,
            limit=page_size,
        )
        total = service.count_activities(
            entity_type=entity_type,
            entity_id=entity_id,
            tenant_id=current_user.tenant_id,
            activity_type=activity_type,
        )
    else:
        activities = service.repository.get_all(
            current_user.tenant_id, activity_type, skip, page_size
        )
        total = service.count_all_activities(
            tenant_id=current_user.tenant_id,
            activity_type=activity_type,
        )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[ActivityResponse.model_validate(a) for a in activities],
        meta={
            "total": total,
            "page": page,
            "page_size": (
                max(page_size, 1) if total == 0 else page_size
            ),  # Minimum page_size is 1
            "total_pages": total_pages,
        },
    )


@router.get(
    "/{activity_id}",
    response_model=StandardResponse[ActivityResponse],
    status_code=status.HTTP_200_OK,
    summary="Get activity",
    description="Get a specific activity by ID. Requires activities.view permission.",
)
async def get_activity(
    current_user: Annotated[User, Depends(require_permission("activities.view"))],
    service: Annotated[ActivityService, Depends(get_activity_service)],
    activity_id: UUID = Path(..., description="Activity ID"),
) -> StandardResponse[ActivityResponse]:
    """Get a specific activity."""
    activity = service.repository.get_by_id(activity_id, current_user.tenant_id)
    if not activity:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ACTIVITY_NOT_FOUND",
            message=f"Activity with ID {activity_id} not found",
        )

    return StandardResponse(
        data=ActivityResponse.model_validate(activity),
        message="Activity retrieved successfully",
    )


@router.put(
    "/{activity_id}",
    response_model=StandardResponse[ActivityResponse],
    status_code=status.HTTP_200_OK,
    summary="Update activity",
    description="Update an activity. Requires activities.manage permission.",
)
async def update_activity(
    activity_data: ActivityUpdate,
    current_user: Annotated[User, Depends(require_permission("activities.manage"))],
    service: Annotated[ActivityService, Depends(get_activity_service)],
    activity_id: UUID = Path(..., description="Activity ID"),
) -> StandardResponse[ActivityResponse]:
    """Update an activity."""
    activity = service.update_activity(
        activity_id=activity_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        title=activity_data.title,
        description=activity_data.description,
        metadata=activity_data.metadata,
    )

    if not activity:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ACTIVITY_NOT_FOUND",
            message=f"Activity with ID {activity_id} not found",
        )

    return StandardResponse(
        data=ActivityResponse.model_validate(activity),
        message="Activity updated successfully",
    )


@router.delete(
    "/{activity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete activity",
    description="Delete an activity. Requires activities.manage permission.",
)
async def delete_activity(
    current_user: Annotated[User, Depends(require_permission("activities.manage"))],
    service: Annotated[ActivityService, Depends(get_activity_service)],
    activity_id: UUID = Path(..., description="Activity ID"),
) -> None:
    """Delete an activity."""
    deleted = service.delete_activity(
        activity_id, current_user.tenant_id, current_user.id
    )
    if not deleted:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ACTIVITY_NOT_FOUND",
            message=f"Activity with ID {activity_id} not found",
        )


@router.get(
    "/entity/{entity_type}/{entity_id}",
    response_model=StandardListResponse[ActivityResponse],
    status_code=status.HTTP_200_OK,
    summary="Get entity timeline",
    description="Get timeline of activities for a specific entity. Requires activities.view permission.",
)
async def get_entity_timeline(
    current_user: Annotated[User, Depends(require_permission("activities.view"))],
    service: Annotated[ActivityService, Depends(get_activity_service)],
    entity_type: str = Path(..., description="Entity type"),
    entity_id: UUID = Path(..., description="Entity ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    activity_type: str | None = Query(None, description="Filter by activity type"),
) -> StandardListResponse[ActivityResponse]:
    """Get timeline of activities for a specific entity."""
    skip = (page - 1) * page_size
    activities = service.get_activities(
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=current_user.tenant_id,
        activity_type=activity_type,
        skip=skip,
        limit=page_size,
    )

    total = service.count_activities(
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=current_user.tenant_id,
        activity_type=activity_type,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[ActivityResponse.model_validate(a) for a in activities],
        meta={
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
        message="Entity timeline retrieved successfully",
    )
