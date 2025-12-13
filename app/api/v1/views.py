"""Views router for saved filters and custom views management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.views.service import ViewService
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.view import (
    CustomViewCreate,
    CustomViewResponse,
    CustomViewUpdate,
    SavedFilterCreate,
    SavedFilterResponse,
    SavedFilterUpdate,
    ViewShareCreate,
    ViewShareResponse,
)

router = APIRouter()


def get_view_service(
    db: Annotated[Session, Depends(get_db)],
) -> ViewService:
    """Dependency to get ViewService."""
    return ViewService(db)


# Saved Filter endpoints
@router.post(
    "/filters",
    response_model=StandardResponse[SavedFilterResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create saved filter",
    description="Create a new saved filter. Requires views.manage permission.",
)
async def create_saved_filter(
    filter_data: SavedFilterCreate,
    current_user: Annotated[User, Depends(require_permission("views.manage"))],
    service: Annotated[ViewService, Depends(get_view_service)],
) -> StandardResponse[SavedFilterResponse]:
    """Create a new saved filter."""
    filter_obj = service.create_saved_filter(
        filter_data=filter_data.model_dump(exclude_none=True),
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

    return StandardResponse(
        data=SavedFilterResponse.model_validate(filter_obj),
        message="Saved filter created successfully",
    )


@router.get(
    "/filters",
    response_model=StandardListResponse[SavedFilterResponse],
    status_code=status.HTTP_200_OK,
    summary="List saved filters",
    description="List saved filters. Requires views.view permission.",
)
async def list_saved_filters(
    current_user: Annotated[User, Depends(require_permission("views.view"))],
    service: Annotated[ViewService, Depends(get_view_service)],
    module: str | None = Query(None, description="Filter by module"),
    is_shared: bool | None = Query(None, description="Filter by shared status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[SavedFilterResponse]:
    """List saved filters."""
    skip = (page - 1) * page_size
    filters = service.get_saved_filters(
        tenant_id=current_user.tenant_id,
        module=module,
        user_id=current_user.id,
        is_shared=is_shared,
        skip=skip,
        limit=page_size,
    )

    total = len(filters)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[SavedFilterResponse.model_validate(f) for f in filters],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Saved filters retrieved successfully",
    )


@router.get(
    "/filters/{filter_id}",
    response_model=StandardResponse[SavedFilterResponse],
    status_code=status.HTTP_200_OK,
    summary="Get saved filter",
    description="Get a specific saved filter by ID. Requires views.view permission.",
)
async def get_saved_filter(
    filter_id: UUID = Path(..., description="Saved filter ID"),
    current_user: Annotated[User, Depends(require_permission("views.view"))],
    service: Annotated[ViewService, Depends(get_view_service)],
) -> StandardResponse[SavedFilterResponse]:
    """Get a specific saved filter."""
    filter_obj = service.get_saved_filter(filter_id, current_user.tenant_id)
    if not filter_obj:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="FILTER_NOT_FOUND",
            message=f"Saved filter with ID {filter_id} not found",
        )

    return StandardResponse(
        data=SavedFilterResponse.model_validate(filter_obj),
        message="Saved filter retrieved successfully",
    )


@router.put(
    "/filters/{filter_id}",
    response_model=StandardResponse[SavedFilterResponse],
    status_code=status.HTTP_200_OK,
    summary="Update saved filter",
    description="Update a saved filter. Requires views.manage permission.",
)
async def update_saved_filter(
    filter_id: UUID = Path(..., description="Saved filter ID"),
    filter_data: SavedFilterUpdate = ...,
    current_user: Annotated[User, Depends(require_permission("views.manage"))],
    service: Annotated[ViewService, Depends(get_view_service)],
) -> StandardResponse[SavedFilterResponse]:
    """Update a saved filter."""
    filter_obj = service.update_saved_filter(
        filter_id=filter_id,
        tenant_id=current_user.tenant_id,
        filter_data=filter_data.model_dump(exclude_none=True),
    )

    if not filter_obj:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="FILTER_NOT_FOUND",
            message=f"Saved filter with ID {filter_id} not found",
        )

    return StandardResponse(
        data=SavedFilterResponse.model_validate(filter_obj),
        message="Saved filter updated successfully",
    )


@router.delete(
    "/filters/{filter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete saved filter",
    description="Delete a saved filter. Requires views.manage permission.",
)
async def delete_saved_filter(
    filter_id: UUID = Path(..., description="Saved filter ID"),
    current_user: Annotated[User, Depends(require_permission("views.manage"))],
    service: Annotated[ViewService, Depends(get_view_service)],
) -> None:
    """Delete a saved filter."""
    success = service.delete_saved_filter(filter_id, current_user.tenant_id)
    if not success:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="FILTER_NOT_FOUND",
            message=f"Saved filter with ID {filter_id} not found",
        )


# Custom View endpoints
@router.post(
    "/views",
    response_model=StandardResponse[CustomViewResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create custom view",
    description="Create a new custom view. Requires views.manage permission.",
)
async def create_custom_view(
    view_data: CustomViewCreate,
    current_user: Annotated[User, Depends(require_permission("views.manage"))],
    service: Annotated[ViewService, Depends(get_view_service)],
) -> StandardResponse[CustomViewResponse]:
    """Create a new custom view."""
    view = service.create_custom_view(
        view_data=view_data.model_dump(exclude_none=True),
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

    return StandardResponse(
        data=CustomViewResponse.model_validate(view),
        message="Custom view created successfully",
    )


@router.get(
    "/views",
    response_model=StandardListResponse[CustomViewResponse],
    status_code=status.HTTP_200_OK,
    summary="List custom views",
    description="List custom views. Requires views.view permission.",
)
async def list_custom_views(
    current_user: Annotated[User, Depends(require_permission("views.view"))],
    service: Annotated[ViewService, Depends(get_view_service)],
    module: str | None = Query(None, description="Filter by module"),
    is_shared: bool | None = Query(None, description="Filter by shared status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[CustomViewResponse]:
    """List custom views."""
    skip = (page - 1) * page_size
    views = service.get_custom_views(
        tenant_id=current_user.tenant_id,
        module=module,
        user_id=current_user.id,
        is_shared=is_shared,
        skip=skip,
        limit=page_size,
    )

    total = len(views)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[CustomViewResponse.model_validate(v) for v in views],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Custom views retrieved successfully",
    )


@router.get(
    "/views/{view_id}",
    response_model=StandardResponse[CustomViewResponse],
    status_code=status.HTTP_200_OK,
    summary="Get custom view",
    description="Get a specific custom view by ID. Requires views.view permission.",
)
async def get_custom_view(
    view_id: UUID = Path(..., description="Custom view ID"),
    current_user: Annotated[User, Depends(require_permission("views.view"))],
    service: Annotated[ViewService, Depends(get_view_service)],
) -> StandardResponse[CustomViewResponse]:
    """Get a specific custom view."""
    view = service.get_custom_view(view_id, current_user.tenant_id)
    if not view:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="VIEW_NOT_FOUND",
            message=f"Custom view with ID {view_id} not found",
        )

    return StandardResponse(
        data=CustomViewResponse.model_validate(view),
        message="Custom view retrieved successfully",
    )


@router.put(
    "/views/{view_id}",
    response_model=StandardResponse[CustomViewResponse],
    status_code=status.HTTP_200_OK,
    summary="Update custom view",
    description="Update a custom view. Requires views.manage permission.",
)
async def update_custom_view(
    view_id: UUID = Path(..., description="Custom view ID"),
    view_data: CustomViewUpdate = ...,
    current_user: Annotated[User, Depends(require_permission("views.manage"))],
    service: Annotated[ViewService, Depends(get_view_service)],
) -> StandardResponse[CustomViewResponse]:
    """Update a custom view."""
    view = service.update_custom_view(
        view_id=view_id,
        tenant_id=current_user.tenant_id,
        view_data=view_data.model_dump(exclude_none=True),
    )

    if not view:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="VIEW_NOT_FOUND",
            message=f"Custom view with ID {view_id} not found",
        )

    return StandardResponse(
        data=CustomViewResponse.model_validate(view),
        message="Custom view updated successfully",
    )


@router.delete(
    "/views/{view_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete custom view",
    description="Delete a custom view. Requires views.manage permission.",
)
async def delete_custom_view(
    view_id: UUID = Path(..., description="Custom view ID"),
    current_user: Annotated[User, Depends(require_permission("views.manage"))],
    service: Annotated[ViewService, Depends(get_view_service)],
) -> None:
    """Delete a custom view."""
    success = service.delete_custom_view(view_id, current_user.tenant_id)
    if not success:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="VIEW_NOT_FOUND",
            message=f"Custom view with ID {view_id} not found",
        )


# View Share endpoints
@router.post(
    "/filters/{filter_id}/share",
    response_model=StandardResponse[ViewShareResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Share filter",
    description="Share a filter with other users. Requires views.share permission.",
)
async def share_filter(
    filter_id: UUID = Path(..., description="Filter ID"),
    share_data: ViewShareCreate = ...,
    current_user: Annotated[User, Depends(require_permission("views.share"))],
    service: Annotated[ViewService, Depends(get_view_service)],
) -> StandardResponse[ViewShareResponse]:
    """Share a filter with other users."""
    share = service.share_filter(
        filter_id=filter_id,
        tenant_id=current_user.tenant_id,
        share_data=share_data.model_dump(exclude_none=True),
    )

    return StandardResponse(
        data=ViewShareResponse.model_validate(share),
        message="Filter shared successfully",
    )


@router.post(
    "/views/{view_id}/share",
    response_model=StandardResponse[ViewShareResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Share view",
    description="Share a view with other users. Requires views.share permission.",
)
async def share_view(
    view_id: UUID = Path(..., description="View ID"),
    share_data: ViewShareCreate = ...,
    current_user: Annotated[User, Depends(require_permission("views.share"))],
    service: Annotated[ViewService, Depends(get_view_service)],
) -> StandardResponse[ViewShareResponse]:
    """Share a view with other users."""
    share = service.share_view(
        view_id=view_id,
        tenant_id=current_user.tenant_id,
        share_data=share_data.model_dump(exclude_none=True),
    )

    return StandardResponse(
        data=ViewShareResponse.model_validate(share),
        message="View shared successfully",
    )

