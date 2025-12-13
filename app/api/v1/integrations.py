"""Integrations router for external integrations and webhooks."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.integrations.service import IntegrationService
from app.core.integrations.webhooks import WebhookHandler
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.integration import (
    IntegrationCreate,
    IntegrationLogResponse,
    IntegrationResponse,
    IntegrationUpdate,
    WebhookCreate,
    WebhookDeliveryResponse,
    WebhookResponse,
    WebhookUpdate,
)

router = APIRouter()


def get_integration_service(db: Annotated[Session, Depends(get_db)]) -> IntegrationService:
    """Dependency to get IntegrationService."""
    return IntegrationService(db)


def get_webhook_handler(db: Annotated[Session, Depends(get_db)]) -> WebhookHandler:
    """Dependency to get WebhookHandler."""
    return WebhookHandler(db)


# Integration endpoints
@router.post(
    "",
    response_model=StandardResponse[IntegrationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create integration",
    description="Create a new integration. Requires integrations.manage permission.",
)
async def create_integration(
    integration_data: IntegrationCreate,
    current_user: Annotated[User, Depends(require_permission("integrations.manage"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> StandardResponse[IntegrationResponse]:
    """Create a new integration."""
    integration = service.create_integration(
        name=integration_data.name,
        tenant_id=current_user.tenant_id,
        integration_type=integration_data.integration_type,
        config=integration_data.config,
        credentials=integration_data.credentials,
        description=integration_data.description,
        metadata=integration_data.metadata,
    )

    return StandardResponse(
        data=IntegrationResponse.model_validate(integration),
        message="Integration created successfully",
    )


@router.get(
    "",
    response_model=StandardListResponse[IntegrationResponse],
    status_code=status.HTTP_200_OK,
    summary="List integrations",
    description="List integrations. Requires integrations.view permission.",
)
async def list_integrations(
    current_user: Annotated[User, Depends(require_permission("integrations.view"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    integration_type: str | None = Query(None, description="Filter by integration type"),
    status: str | None = Query(None, description="Filter by status"),
) -> StandardListResponse[IntegrationResponse]:
    """List integrations."""
    skip = (page - 1) * page_size
    integrations = service.get_integrations(
        tenant_id=current_user.tenant_id,
        integration_type=integration_type,
        status=status,
        skip=skip,
        limit=page_size,
    )
    total = len(integrations)  # TODO: Add count method to repository

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[IntegrationResponse.model_validate(i) for i in integrations],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Integrations retrieved successfully",
    )


@router.get(
    "/{integration_id}",
    response_model=StandardResponse[IntegrationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get integration",
    description="Get a specific integration by ID. Requires integrations.view permission.",
)
async def get_integration(
    integration_id: UUID = Path(..., description="Integration ID"),
    current_user: Annotated[User, Depends(require_permission("integrations.view"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> StandardResponse[IntegrationResponse]:
    """Get a specific integration."""
    integration = service.get_integration(integration_id, current_user.tenant_id)
    if not integration:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="INTEGRATION_NOT_FOUND",
            message=f"Integration with ID {integration_id} not found",
        )

    return StandardResponse(
        data=IntegrationResponse.model_validate(integration),
        message="Integration retrieved successfully",
    )


@router.put(
    "/{integration_id}",
    response_model=StandardResponse[IntegrationResponse],
    status_code=status.HTTP_200_OK,
    summary="Update integration",
    description="Update an integration. Requires integrations.manage permission.",
)
async def update_integration(
    integration_id: UUID = Path(..., description="Integration ID"),
    integration_data: IntegrationUpdate = ...,
    current_user: Annotated[User, Depends(require_permission("integrations.manage"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> StandardResponse[IntegrationResponse]:
    """Update an integration."""
    update_dict = integration_data.model_dump(exclude_unset=True)
    integration = service.update_integration(integration_id, current_user.tenant_id, update_dict)

    if not integration:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="INTEGRATION_NOT_FOUND",
            message=f"Integration with ID {integration_id} not found",
        )

    return StandardResponse(
        data=IntegrationResponse.model_validate(integration),
        message="Integration updated successfully",
    )


@router.delete(
    "/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete integration",
    description="Delete an integration. Requires integrations.manage permission.",
)
async def delete_integration(
    integration_id: UUID = Path(..., description="Integration ID"),
    current_user: Annotated[User, Depends(require_permission("integrations.manage"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> None:
    """Delete an integration."""
    deleted = service.delete_integration(integration_id, current_user.tenant_id)
    if not deleted:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="INTEGRATION_NOT_FOUND",
            message=f"Integration with ID {integration_id} not found",
        )


@router.get(
    "/{integration_id}/logs",
    response_model=StandardListResponse[IntegrationLogResponse],
    status_code=status.HTTP_200_OK,
    summary="Get integration logs",
    description="Get logs for an integration. Requires integrations.view permission.",
)
async def get_integration_logs(
    integration_id: UUID = Path(..., description="Integration ID"),
    current_user: Annotated[User, Depends(require_permission("integrations.view"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[IntegrationLogResponse]:
    """Get logs for an integration."""
    skip = (page - 1) * page_size
    logs = service.get_logs(integration_id, current_user.tenant_id, skip, page_size)
    total = len(logs)  # TODO: Add count method to repository

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[IntegrationLogResponse.model_validate(l) for l in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Integration logs retrieved successfully",
    )


# Webhook endpoints
@router.post(
    "/webhooks",
    response_model=StandardResponse[WebhookResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create webhook",
    description="Create a new webhook. Requires integrations.manage permission.",
)
async def create_webhook(
    webhook_data: WebhookCreate,
    current_user: Annotated[User, Depends(require_permission("integrations.manage"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> StandardResponse[WebhookResponse]:
    """Create a new webhook."""
    from app.repositories.integration_repository import IntegrationRepository

    repository = IntegrationRepository(service.db)
    webhook = repository.create_webhook(
        {
            "tenant_id": current_user.tenant_id,
            "integration_id": webhook_data.integration_id,
            "name": webhook_data.name,
            "url": webhook_data.url,
            "event_type": webhook_data.event_type,
            "enabled": webhook_data.enabled,
            "method": webhook_data.method,
            "headers": webhook_data.headers,
            "secret": webhook_data.secret,
            "max_retries": webhook_data.max_retries,
            "retry_delay": webhook_data.retry_delay,
            "metadata": webhook_data.metadata,
        }
    )

    return StandardResponse(
        data=WebhookResponse.model_validate(webhook),
        message="Webhook created successfully",
    )


@router.get(
    "/webhooks",
    response_model=StandardListResponse[WebhookResponse],
    status_code=status.HTTP_200_OK,
    summary="List webhooks",
    description="List webhooks. Requires integrations.view permission.",
)
async def list_webhooks(
    current_user: Annotated[User, Depends(require_permission("integrations.view"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    enabled_only: bool = Query(default=False, description="Only return enabled webhooks"),
) -> StandardListResponse[WebhookResponse]:
    """List webhooks."""
    from app.repositories.integration_repository import IntegrationRepository

    repository = IntegrationRepository(service.db)
    skip = (page - 1) * page_size
    webhooks = repository.get_all_webhooks(
        current_user.tenant_id, enabled_only=enabled_only, skip=skip, limit=page_size
    )
    total = len(webhooks)  # TODO: Add count method to repository

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[WebhookResponse.model_validate(w) for w in webhooks],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Webhooks retrieved successfully",
    )


@router.get(
    "/webhooks/{webhook_id}",
    response_model=StandardResponse[WebhookResponse],
    status_code=status.HTTP_200_OK,
    summary="Get webhook",
    description="Get a specific webhook by ID. Requires integrations.view permission.",
)
async def get_webhook(
    webhook_id: UUID = Path(..., description="Webhook ID"),
    current_user: Annotated[User, Depends(require_permission("integrations.view"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> StandardResponse[WebhookResponse]:
    """Get a specific webhook."""
    from app.repositories.integration_repository import IntegrationRepository

    repository = IntegrationRepository(service.db)
    webhook = repository.get_webhook_by_id(webhook_id, current_user.tenant_id)
    if not webhook:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="WEBHOOK_NOT_FOUND",
            message=f"Webhook with ID {webhook_id} not found",
        )

    return StandardResponse(
        data=WebhookResponse.model_validate(webhook),
        message="Webhook retrieved successfully",
    )


@router.put(
    "/webhooks/{webhook_id}",
    response_model=StandardResponse[WebhookResponse],
    status_code=status.HTTP_200_OK,
    summary="Update webhook",
    description="Update a webhook. Requires integrations.manage permission.",
)
async def update_webhook(
    webhook_id: UUID = Path(..., description="Webhook ID"),
    webhook_data: WebhookUpdate = ...,
    current_user: Annotated[User, Depends(require_permission("integrations.manage"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> StandardResponse[WebhookResponse]:
    """Update a webhook."""
    from app.repositories.integration_repository import IntegrationRepository

    repository = IntegrationRepository(service.db)
    update_dict = webhook_data.model_dump(exclude_unset=True)
    webhook = repository.update_webhook(webhook_id, current_user.tenant_id, update_dict)

    if not webhook:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="WEBHOOK_NOT_FOUND",
            message=f"Webhook with ID {webhook_id} not found",
        )

    return StandardResponse(
        data=WebhookResponse.model_validate(webhook),
        message="Webhook updated successfully",
    )


@router.delete(
    "/webhooks/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete webhook",
    description="Delete a webhook. Requires integrations.manage permission.",
)
async def delete_webhook(
    webhook_id: UUID = Path(..., description="Webhook ID"),
    current_user: Annotated[User, Depends(require_permission("integrations.manage"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> None:
    """Delete a webhook."""
    from app.repositories.integration_repository import IntegrationRepository

    repository = IntegrationRepository(service.db)
    deleted = repository.delete_webhook(webhook_id, current_user.tenant_id)
    if not deleted:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="WEBHOOK_NOT_FOUND",
            message=f"Webhook with ID {webhook_id} not found",
        )


@router.get(
    "/webhooks/{webhook_id}/deliveries",
    response_model=StandardListResponse[WebhookDeliveryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get webhook deliveries",
    description="Get deliveries for a webhook. Requires integrations.view permission.",
)
async def get_webhook_deliveries(
    webhook_id: UUID = Path(..., description="Webhook ID"),
    current_user: Annotated[User, Depends(require_permission("integrations.view"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    status: str | None = Query(None, description="Filter by delivery status"),
) -> StandardListResponse[WebhookDeliveryResponse]:
    """Get deliveries for a webhook."""
    from app.repositories.integration_repository import IntegrationRepository

    repository = IntegrationRepository(service.db)
    skip = (page - 1) * page_size
    deliveries = repository.get_deliveries_by_webhook(
        webhook_id, current_user.tenant_id, status, skip, page_size
    )
    total = len(deliveries)  # TODO: Add count method to repository

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[WebhookDeliveryResponse.model_validate(d) for d in deliveries],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Webhook deliveries retrieved successfully",
    )

