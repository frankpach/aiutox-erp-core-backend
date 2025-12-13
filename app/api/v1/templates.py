"""Templates router for document and notification template management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.templates.service import TemplateService
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.template import (
    TemplateCategoryCreate,
    TemplateCategoryResponse,
    TemplateCreate,
    TemplateRenderRequest,
    TemplateRenderResponse,
    TemplateResponse,
    TemplateUpdate,
    TemplateVersionResponse,
)

router = APIRouter()


def get_template_service(
    db: Annotated[Session, Depends(get_db)],
) -> TemplateService:
    """Dependency to get TemplateService."""
    return TemplateService(db)


# Template endpoints
@router.post(
    "",
    response_model=StandardResponse[TemplateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create template",
    description="Create a new template. Requires templates.manage permission.",
)
async def create_template(
    template_data: TemplateCreate,
    current_user: Annotated[User, Depends(require_permission("templates.manage"))],
    service: Annotated[TemplateService, Depends(get_template_service)],
) -> StandardResponse[TemplateResponse]:
    """Create a new template."""
    template = service.create_template(
        template_data=template_data.model_dump(exclude_none=True),
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

    return StandardResponse(
        data=TemplateResponse.model_validate(template),
        message="Template created successfully",
    )


@router.get(
    "",
    response_model=StandardListResponse[TemplateResponse],
    status_code=status.HTTP_200_OK,
    summary="List templates",
    description="List templates. Requires templates.view permission.",
)
async def list_templates(
    current_user: Annotated[User, Depends(require_permission("templates.view"))],
    service: Annotated[TemplateService, Depends(get_template_service)],
    template_type: str | None = Query(None, description="Filter by template type"),
    category: str | None = Query(None, description="Filter by category"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[TemplateResponse]:
    """List templates."""
    skip = (page - 1) * page_size
    templates = service.get_templates(
        tenant_id=current_user.tenant_id,
        template_type=template_type,
        category=category,
        is_active=is_active,
        skip=skip,
        limit=page_size,
    )

    total = len(templates)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[TemplateResponse.model_validate(t) for t in templates],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Templates retrieved successfully",
    )


@router.get(
    "/{template_id}",
    response_model=StandardResponse[TemplateResponse],
    status_code=status.HTTP_200_OK,
    summary="Get template",
    description="Get a specific template by ID. Requires templates.view permission.",
)
async def get_template(
    template_id: UUID = Path(..., description="Template ID"),
    current_user: Annotated[User, Depends(require_permission("templates.view"))],
    service: Annotated[TemplateService, Depends(get_template_service)],
) -> StandardResponse[TemplateResponse]:
    """Get a specific template."""
    template = service.get_template(template_id, current_user.tenant_id)
    if not template:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TEMPLATE_NOT_FOUND",
            message=f"Template with ID {template_id} not found",
        )

    return StandardResponse(
        data=TemplateResponse.model_validate(template),
        message="Template retrieved successfully",
    )


@router.put(
    "/{template_id}",
    response_model=StandardResponse[TemplateResponse],
    status_code=status.HTTP_200_OK,
    summary="Update template",
    description="Update a template. Requires templates.manage permission.",
)
async def update_template(
    template_id: UUID = Path(..., description="Template ID"),
    template_data: TemplateUpdate = ...,
    current_user: Annotated[User, Depends(require_permission("templates.manage"))],
    service: Annotated[TemplateService, Depends(get_template_service)],
) -> StandardResponse[TemplateResponse]:
    """Update a template."""
    template = service.update_template(
        template_id=template_id,
        tenant_id=current_user.tenant_id,
        template_data=template_data.model_dump(exclude_none=True),
    )

    if not template:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TEMPLATE_NOT_FOUND",
            message=f"Template with ID {template_id} not found",
        )

    return StandardResponse(
        data=TemplateResponse.model_validate(template),
        message="Template updated successfully",
    )


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete template",
    description="Delete a template. Requires templates.manage permission.",
)
async def delete_template(
    template_id: UUID = Path(..., description="Template ID"),
    current_user: Annotated[User, Depends(require_permission("templates.manage"))],
    service: Annotated[TemplateService, Depends(get_template_service)],
) -> None:
    """Delete a template."""
    try:
        success = service.delete_template(template_id, current_user.tenant_id)
        if not success:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="TEMPLATE_NOT_FOUND",
                message=f"Template with ID {template_id} not found",
            )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="TEMPLATE_DELETE_ERROR",
            message=str(e),
        )


@router.get(
    "/{template_id}/versions",
    response_model=StandardListResponse[TemplateVersionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get template versions",
    description="Get template versions. Requires templates.view permission.",
)
async def get_template_versions(
    template_id: UUID = Path(..., description="Template ID"),
    current_user: Annotated[User, Depends(require_permission("templates.view"))],
    service: Annotated[TemplateService, Depends(get_template_service)],
) -> StandardListResponse[TemplateVersionResponse]:
    """Get template versions."""
    versions = service.get_template_versions(template_id, current_user.tenant_id)

    return StandardListResponse(
        data=[TemplateVersionResponse.model_validate(v) for v in versions],
        total=len(versions),
        page=1,
        page_size=len(versions),
        total_pages=1,
        message="Template versions retrieved successfully",
    )


@router.post(
    "/{template_id}/render",
    response_model=StandardResponse[TemplateRenderResponse],
    status_code=status.HTTP_200_OK,
    summary="Render template",
    description="Render a template with variables. Requires templates.render permission.",
)
async def render_template(
    template_id: UUID = Path(..., description="Template ID"),
    render_request: TemplateRenderRequest = ...,
    current_user: Annotated[User, Depends(require_permission("templates.render"))],
    service: Annotated[TemplateService, Depends(get_template_service)],
) -> StandardResponse[TemplateRenderResponse]:
    """Render a template with variables."""
    try:
        result = service.render_template(
            template_id=template_id,
            tenant_id=current_user.tenant_id,
            variables=render_request.variables,
            format=render_request.format,
        )

        return StandardResponse(
            data=TemplateRenderResponse(**result),
            message="Template rendered successfully",
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TEMPLATE_NOT_FOUND",
            message=str(e),
        )

