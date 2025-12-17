"""Tags router for tag management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.tags.service import TagService
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.tag import (
    TagCategoryCreate,
    TagCategoryResponse,
    TagCreate,
    TagResponse,
    TagUpdate,
)

router = APIRouter()


def get_tag_service(db: Annotated[Session, Depends(get_db)]) -> TagService:
    """Dependency to get TagService."""
    return TagService(db)


@router.post(
    "",
    response_model=StandardResponse[TagResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create tag",
    description="Create a new tag. Requires tags.manage permission.",
)
async def create_tag(
    tag_data: TagCreate,
    current_user: Annotated[User, Depends(require_permission("tags.manage"))],
    service: Annotated[TagService, Depends(get_tag_service)],
) -> StandardResponse[TagResponse]:
    """Create a new tag."""
    tag = service.create_tag(
        name=tag_data.name,
        tenant_id=current_user.tenant_id,
        color=tag_data.color,
        description=tag_data.description,
        category_id=tag_data.category_id,
    )

    return StandardResponse(
        data=TagResponse.model_validate(tag),
        message="Tag created successfully",
    )


@router.get(
    "",
    response_model=StandardListResponse[TagResponse],
    status_code=status.HTTP_200_OK,
    summary="List tags",
    description="List all tags for the current tenant. Requires tags.view permission.",
)
async def list_tags(
    current_user: Annotated[User, Depends(require_permission("tags.view"))],
    service: Annotated[TagService, Depends(get_tag_service)],
    category_id: UUID | None = Query(default=None, description="Filter by category"),
    search: str | None = Query(default=None, description="Search by name"),
) -> StandardListResponse[TagResponse]:
    """List all tags."""
    if search:
        tags = service.search_tags(current_user.tenant_id, search)
        total = len(tags)
    else:
        tags = service.get_all_tags(current_user.tenant_id, category_id=category_id)
        total = len(tags)

    return StandardListResponse(
        data=[TagResponse.model_validate(t) for t in tags],
        meta={
            "total": total,
            "page": 1,
            "page_size": max(1, total) if total > 0 else 20,
            "total_pages": 1,
        },
        message="Tags retrieved successfully",
    )


@router.get(
    "/{tag_id}",
    response_model=StandardResponse[TagResponse],
    status_code=status.HTTP_200_OK,
    summary="Get tag",
    description="Get a specific tag by ID. Requires tags.view permission.",
)
async def get_tag(
    tag_id: Annotated[UUID, Path(..., description="Tag ID")],
    current_user: Annotated[User, Depends(require_permission("tags.view"))],
    service: Annotated[TagService, Depends(get_tag_service)],
) -> StandardResponse[TagResponse]:
    """Get a specific tag."""
    tag = service.repository.get_tag_by_id(tag_id, current_user.tenant_id)
    if not tag:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TAG_NOT_FOUND",
            message=f"Tag with ID {tag_id} not found",
        )

    return StandardResponse(
        data=TagResponse.model_validate(tag),
        message="Tag retrieved successfully",
    )


@router.put(
    "/{tag_id}",
    response_model=StandardResponse[TagResponse],
    status_code=status.HTTP_200_OK,
    summary="Update tag",
    description="Update a tag. Requires tags.manage permission.",
)
async def update_tag(
    tag_id: Annotated[UUID, Path(..., description="Tag ID")],
    current_user: Annotated[User, Depends(require_permission("tags.manage"))],
    service: Annotated[TagService, Depends(get_tag_service)],
    tag_data: TagUpdate,
) -> StandardResponse[TagResponse]:
    """Update a tag."""
    tag = service.update_tag(
        tag_id=tag_id,
        tenant_id=current_user.tenant_id,
        name=tag_data.name,
        color=tag_data.color,
        description=tag_data.description,
        category_id=tag_data.category_id,
    )

    if not tag:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TAG_NOT_FOUND",
            message=f"Tag with ID {tag_id} not found",
        )

    return StandardResponse(
        data=TagResponse.model_validate(tag),
        message="Tag updated successfully",
    )


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tag",
    description="Delete a tag (soft delete). Requires tags.manage permission.",
)
async def delete_tag(
    tag_id: Annotated[UUID, Path(..., description="Tag ID")],
    current_user: Annotated[User, Depends(require_permission("tags.manage"))],
    service: Annotated[TagService, Depends(get_tag_service)],
) -> None:
    """Delete a tag."""
    deleted = service.delete_tag(tag_id, current_user.tenant_id)
    if not deleted:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TAG_NOT_FOUND",
            message=f"Tag with ID {tag_id} not found",
        )


@router.post(
    "/{tag_id}/entities/{entity_type}/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Add tag to entity",
    description="Add a tag to an entity. Requires tags.manage permission.",
)
async def add_tag_to_entity(
    tag_id: Annotated[UUID, Path(..., description="Tag ID")],
    entity_type: Annotated[str, Path(..., description="Entity type")],
    entity_id: Annotated[UUID, Path(..., description="Entity ID")],
    current_user: Annotated[User, Depends(require_permission("tags.manage"))],
    service: Annotated[TagService, Depends(get_tag_service)],
) -> None:
    """Add a tag to an entity."""
    try:
        service.add_tag_to_entity(
            tag_id=tag_id,
            entity_type=entity_type,
            entity_id=entity_id,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="TAG_OPERATION_FAILED",
            message=str(e),
        )


@router.delete(
    "/{tag_id}/entities/{entity_type}/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove tag from entity",
    description="Remove a tag from an entity. Requires tags.manage permission.",
)
async def remove_tag_from_entity(
    tag_id: Annotated[UUID, Path(..., description="Tag ID")],
    entity_type: Annotated[str, Path(..., description="Entity type")],
    entity_id: Annotated[UUID, Path(..., description="Entity ID")],
    current_user: Annotated[User, Depends(require_permission("tags.manage"))],
    service: Annotated[TagService, Depends(get_tag_service)],
) -> None:
    """Remove a tag from an entity."""
    removed = service.remove_tag_from_entity(
        tag_id=tag_id,
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=current_user.tenant_id,
    )
    if not removed:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ENTITY_TAG_NOT_FOUND",
            message=f"Tag {tag_id} not found on entity {entity_type}:{entity_id}",
        )


@router.get(
    "/entities/{entity_type}/{entity_id}",
    response_model=StandardListResponse[TagResponse],
    status_code=status.HTTP_200_OK,
    summary="Get entity tags",
    description="Get all tags for an entity. Requires tags.view permission.",
)
async def get_entity_tags(
    entity_type: Annotated[str, Path(..., description="Entity type")],
    entity_id: Annotated[UUID, Path(..., description="Entity ID")],
    current_user: Annotated[User, Depends(require_permission("tags.view"))],
    service: Annotated[TagService, Depends(get_tag_service)],
) -> StandardListResponse[TagResponse]:
    """Get all tags for an entity."""
    tags = service.get_entity_tags(entity_type, entity_id, current_user.tenant_id)

    return StandardListResponse(
        data=[TagResponse.model_validate(t) for t in tags],
        meta={
            "total": len(tags),
            "page": 1,
            "page_size": max(1, len(tags)) if len(tags) > 0 else 20,
            "total_pages": 1,
        },
        message="Entity tags retrieved successfully",
    )


@router.get(
    "/categories",
    response_model=StandardListResponse[TagCategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List tag categories",
    description="List all tag categories. Requires tags.view permission.",
)
async def list_categories(
    current_user: Annotated[User, Depends(require_permission("tags.view"))],
    service: Annotated[TagService, Depends(get_tag_service)],
) -> StandardListResponse[TagCategoryResponse]:
    """List all tag categories."""
    categories = service.get_all_categories(current_user.tenant_id)

    return StandardListResponse(
        data=[TagCategoryResponse.model_validate(c) for c in categories],
        meta={
            "total": len(categories),
            "page": 1,
            "page_size": max(1, len(categories)) if len(categories) > 0 else 20,
            "total_pages": 1,
        },
        message="Tag categories retrieved successfully",
    )


@router.post(
    "/categories",
    response_model=StandardResponse[TagCategoryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create tag category",
    description="Create a new tag category. Requires tags.manage permission.",
)
async def create_category(
    category_data: TagCategoryCreate,
    current_user: Annotated[User, Depends(require_permission("tags.manage"))],
    service: Annotated[TagService, Depends(get_tag_service)],
) -> StandardResponse[TagCategoryResponse]:
    """Create a new tag category."""
    category = service.create_category(
        name=category_data.name,
        tenant_id=current_user.tenant_id,
        color=category_data.color,
        description=category_data.description,
        parent_id=category_data.parent_id,
        sort_order=category_data.sort_order,
    )

    return StandardResponse(
        data=TagCategoryResponse.model_validate(category),
        message="Tag category created successfully",
    )

