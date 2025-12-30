"""Notifications router for notification management."""

import asyncio
import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

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
    event_type: str | None = Query(default=None, description="Filter by event type"),
) -> StandardListResponse[NotificationTemplateResponse]:
    """List all notification templates."""
    skip = (page - 1) * page_size

    # Get total count for accurate pagination
    total = repository.count_templates(
        tenant_id=current_user.tenant_id, event_type=event_type
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Get paginated templates
    templates = repository.get_all_templates(
        tenant_id=current_user.tenant_id, event_type=event_type
    )
    # Apply pagination
    paginated_templates = templates[skip : skip + page_size]

    return StandardListResponse(
        data=[NotificationTemplateResponse.model_validate(t) for t in paginated_templates],
        meta={
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
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
            code="NOTIFICATION_TEMPLATE_NOT_FOUND",
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
            code="NOTIFICATION_TEMPLATE_NOT_FOUND",
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
            code="NOTIFICATION_TEMPLATE_NOT_FOUND",
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
    status: str | None = Query(default=None, description="Filter by status (pending, sent, failed)"),
) -> StandardListResponse[NotificationQueueResponse]:
    """List notification queue entries."""
    skip = (page - 1) * page_size

    # Get total count for accurate pagination
    total = repository.count_queue_entries(
        tenant_id=current_user.tenant_id, status=status
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    queue_entries = repository.get_queue_entries(
        tenant_id=current_user.tenant_id, status=status, skip=skip, limit=page_size
    )

    return StandardListResponse(
        data=[NotificationQueueResponse.model_validate(entry) for entry in queue_entries],
        meta={
            "total": total,
            "page": page,
            "page_size": max(page_size, 1) if total == 0 else page_size,  # Minimum page_size is 1
            "total_pages": total_pages,
        },
    )


@router.get(
    "/queue/{queue_id}",
    response_model=StandardResponse[NotificationQueueResponse],
    status_code=status.HTTP_200_OK,
    summary="Get notification queue entry",
    description="Get a specific notification queue entry by ID. Requires notifications.view permission.",
)
async def get_queue_entry(
    queue_id: Annotated[UUID, Path(..., description="Queue entry ID")],
    current_user: Annotated[User, Depends(require_permission("notifications.view"))],
    repository: Annotated[NotificationRepository, Depends(get_notification_repository)],
) -> StandardResponse[NotificationQueueResponse]:
    """Get a specific notification queue entry."""
    entry = repository.get_queue_entry_by_id(queue_id, current_user.tenant_id)

    if not entry:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOTIFICATION_QUEUE_ENTRY_NOT_FOUND",
            message=f"Queue entry with ID {queue_id} not found",
        )

    return StandardResponse(
        data=NotificationQueueResponse.model_validate(entry),
        message="Queue entry retrieved successfully",
    )


@router.get(
    "/stream",
    summary="Stream notifications (SSE)",
    description="Stream notifications in real-time using Server-Sent Events. Requires notifications.view permission.",
    responses={
        200: {
            "description": "Server-Sent Events stream",
            "content": {"text/event-stream": {}},
        },
    },
)
async def stream_notifications(
    current_user: Annotated[User, Depends(require_permission("notifications.view"))],
    repository: Annotated[NotificationRepository, Depends(get_notification_repository)],
) -> StreamingResponse:
    """Stream notifications using Server-Sent Events.

    This endpoint provides real-time notifications using SSE. The client will receive
    new notifications as they are created. The stream checks for new notifications
    every 5 seconds.

    Example client usage:
        const eventSource = new EventSource('/api/v1/notifications/stream', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        eventSource.onmessage = (event) => {
            const notification = JSON.parse(event.data);
            // Handle notification
        };
    """
    async def event_generator():
        """Generate SSE events for new notifications."""
        last_id = None
        try:
            while True:
                # Get new notifications
                new_notifications = repository.get_unread_notifications(
                    tenant_id=current_user.tenant_id,
                    user_id=current_user.id,
                    since_id=last_id,
                    limit=50,
                )

                # Send each notification as an SSE event
                for notification in new_notifications:
                    notification_data = NotificationQueueResponse.model_validate(
                        notification
                    ).model_dump(mode='json')  # Use mode='json' to serialize UUIDs as strings
                    # Format as SSE: "data: {json}\n\n"
                    yield f"data: {json.dumps(notification_data)}\n\n"
                    last_id = notification.id

                # Wait before next check (5 seconds)
                await asyncio.sleep(5)

        except asyncio.CancelledError:
            # Client disconnected
            logger.info(f"SSE stream disconnected for user {current_user.id}")
            raise
        except Exception as e:
            logger.error(f"Error in SSE stream for user {current_user.id}: {e}", exc_info=True)
            # Send error event
            error_data = {
                "error": {
                    "code": "STREAM_ERROR",
                    "message": "Error in notification stream",
                }
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in Nginx
        },
    )

