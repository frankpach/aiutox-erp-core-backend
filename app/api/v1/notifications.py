"""Notifications router for notification management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.notifications.service import NotificationService
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.notification import (
    NotificationQueueResponse,
    NotificationSendRequest,
    NotificationTemplateCreate,
    NotificationTemplateResponse,
    NotificationTemplateUpdate,
)

router = APIRouter()


def get_notification_service(
    db: Annotated[Session, Depends(get_db)],
) -> NotificationService:
    """Dependency to get NotificationService."""
    return NotificationService(db)


def get_notification_repository(
    db: Annotated[Session, Depends(get_db)],
) -> NotificationRepository:
    """Dependency to get NotificationRepository."""
    return NotificationRepository(db)


@router.post(
    "/templates",
    response_model=StandardResponse[NotificationTemplateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create notification template",
    description="Create a new notification template. Requires notifications.manage permission.",
)
async def create_template(
    template_data: NotificationTemplateCreate,
    current_user: Annotated[User, Depends(require_permission("notifications.manage"))],
    repository: Annotated[NotificationRepository, Depends(get_notification_repository)],
) -> StandardResponse[NotificationTemplateResponse]:
    """Create a new notification template."""
    template = repository.create_template(
        {
            "tenant_id": current_user.tenant_id,
            "name": template_data.name,
            "event_type": template_data.event_type,
            "channel": template_data.channel,
            "subject": template_data.subject,
            "body": template_data.body,
            "is_active": template_data.is_active,
        }
    )

    return StandardResponse(
        data=NotificationTemplateResponse.model_validate(template),
        message="Template created successfully",
    )


@router.get(
    "/templates",
    response_model=StandardListResponse[NotificationTemplateResponse],
    status_code=status.HTTP_200_OK,
    summary="List notification templates",
    description="List all notification templates for the current tenant. Requires notifications.view permission.",
)
async def list_templates(
    current_user: Annotated[User, Depends(require_permission("notifications.view"))],
    repository: Annotated[NotificationRepository, Depends(get_notification_repository)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    event_type: str | None = Query(None, description="Filter by event type"),
) -> StandardListResponse[NotificationTemplateResponse]:
    """List all notification templates."""
    skip = (page - 1) * page_size
    templates = repository.get_all_templates(
        tenant_id=current_user.tenant_id, event_type=event_type
    )

    total = len(templates)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Apply pagination
    paginated_templates = templates[skip : skip + page_size]

    return StandardListResponse(
        data=[NotificationTemplateResponse.model_validate(t) for t in paginated_templates],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Templates retrieved successfully",
    )


@router.get(
    "/templates/{template_id}",
    response_model=StandardResponse[NotificationTemplateResponse],
    status_code=status.HTTP_200_OK,
    summary="Get notification template",
    description="Get a specific notification template by ID. Requires notifications.view permission.",
)
async def get_template(
    template_id: UUID,
    current_user: Annotated[User, Depends(require_permission("notifications.view"))],
    repository: Annotated[NotificationRepository, Depends(get_notification_repository)],
) -> StandardResponse[NotificationTemplateResponse]:
    """Get a specific notification template."""
    # Get all templates and filter by ID and tenant
    templates = repository.get_all_templates(tenant_id=current_user.tenant_id)
    template = next((t for t in templates if t.id == template_id), None)

    if not template:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOTIFICATION_TEMPLATE_NOT_FOUND",
            message=f"Template with ID {template_id} not found",
        )

    return StandardResponse(
        data=NotificationTemplateResponse.model_validate(template),
        message="Template retrieved successfully",
    )


@router.put(
    "/templates/{template_id}",
    response_model=StandardResponse[NotificationTemplateResponse],
    status_code=status.HTTP_200_OK,
    summary="Update notification template",
    description="Update a notification template. Requires notifications.manage permission.",
)
async def update_template(
    template_id: UUID,
    template_data: NotificationTemplateUpdate,
    current_user: Annotated[User, Depends(require_permission("notifications.manage"))],
    repository: Annotated[NotificationRepository, Depends(get_notification_repository)],
) -> StandardResponse[NotificationTemplateResponse]:
    """Update a notification template."""
    # Build update dict with only provided fields
    update_dict = template_data.model_dump(exclude_unset=True)

    template = repository.update_template(template_id, current_user.tenant_id, update_dict)

    if not template:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOTIFICATION_TEMPLATE_NOT_FOUND",
            message=f"Template with ID {template_id} not found",
        )

    return StandardResponse(
        data=NotificationTemplateResponse.model_validate(template),
        message="Template updated successfully",
    )


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete notification template",
    description="Delete a notification template. Requires notifications.manage permission.",
)
async def delete_template(
    template_id: UUID,
    current_user: Annotated[User, Depends(require_permission("notifications.manage"))],
    repository: Annotated[NotificationRepository, Depends(get_notification_repository)],
) -> None:
    """Delete a notification template."""
    deleted = repository.delete_template(template_id, current_user.tenant_id)
    if not deleted:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOTIFICATION_TEMPLATE_NOT_FOUND",
            message=f"Template with ID {template_id} not found",
        )


@router.post(
    "/send",
    response_model=StandardResponse[list[dict]],
    status_code=status.HTTP_200_OK,
    summary="Send notification manually",
    description="Send a notification manually. Requires notifications.manage permission.",
)
async def send_notification(
    request: NotificationSendRequest,
    current_user: Annotated[User, Depends(require_permission("notifications.manage"))],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> StandardResponse[list[dict]]:
    """Send a notification manually."""
    results = await service.send(
        event_type=request.event_type,
        recipient_id=request.recipient_id,
        channels=request.channels,
        data=request.data,
        tenant_id=current_user.tenant_id,
    )

    return StandardResponse(
        data=results,
        message="Notification sent successfully",
    )


@router.get(
    "/queue",
    response_model=StandardListResponse[NotificationQueueResponse],
    status_code=status.HTTP_200_OK,
    summary="List notification queue entries",
    description="List notification queue entries for the current tenant. Requires notifications.view permission.",
)
async def list_queue_entries(
    current_user: Annotated[User, Depends(require_permission("notifications.view"))],
    repository: Annotated[NotificationRepository, Depends(get_notification_repository)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    status: str | None = Query(None, description="Filter by status (pending, sent, failed)"),
) -> StandardListResponse[NotificationQueueResponse]:
    """List notification queue entries."""
    skip = (page - 1) * page_size
    queue_entries = repository.get_queue_entries(
        tenant_id=current_user.tenant_id, status=status, skip=skip, limit=page_size
    )

    # TODO: Add count method to repository for accurate total
    total = len(queue_entries)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[NotificationQueueResponse.model_validate(entry) for entry in queue_entries],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Queue entries retrieved successfully",
    )


@router.get(
    "/queue/{queue_id}",
    response_model=StandardResponse[NotificationQueueResponse],
    status_code=status.HTTP_200_OK,
    summary="Get notification queue entry",
    description="Get a specific notification queue entry by ID. Requires notifications.view permission.",
)
async def get_queue_entry(
    queue_id: UUID = Path(..., description="Queue entry ID"),
    current_user: Annotated[User, Depends(require_permission("notifications.view"))],
    repository: Annotated[NotificationRepository, Depends(get_notification_repository)],
) -> StandardResponse[NotificationQueueResponse]:
    """Get a specific notification queue entry."""
    entry = repository.get_queue_entry_by_id(queue_id, current_user.tenant_id)

    if not entry:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOTIFICATION_QUEUE_ENTRY_NOT_FOUND",
            message=f"Queue entry with ID {queue_id} not found",
        )

    return StandardResponse(
        data=NotificationQueueResponse.model_validate(entry),
        message="Queue entry retrieved successfully",
    )

