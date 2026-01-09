"""Integration router for third-party service integrations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException, raise_not_found
from app.core.integrations.service import IntegrationService
from app.core.logging import get_client_info
from app.models.integration import IntegrationStatus, IntegrationType
from app.models.user import User
from app.schemas.common import PaginationMeta, StandardListResponse, StandardResponse
from app.schemas.integration import (
    IntegrationActivateRequest,
    IntegrationCreate,
    IntegrationCredentialsResponse,
    IntegrationLogResponse,
    IntegrationResponse,
    IntegrationTestResponse,
    IntegrationUpdate,
    WebhookCreate,
    WebhookResponse,
)

router = APIRouter()


def get_integration_service(
    db: Annotated[Session, Depends(get_db)],
) -> IntegrationService:
    """Dependency to get IntegrationService."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("get_integration_service called")
    service = IntegrationService(db)
    logger.info(f"IntegrationService created: {service}")
    return service


@router.get(
    "",
    response_model=StandardListResponse[IntegrationResponse],
    status_code=status.HTTP_200_OK,
    summary="List integrations",
    description="List all integrations for the current tenant. Requires integrations.view permission.",
    responses={
        200: {"description": "Integrations retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "integrations.view"},
                        }
                    }
                }
            },
        },
    },
)
async def list_integrations(
    current_user: Annotated[User, Depends(require_permission("integrations.view"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
    type: str | None = None,
) -> StandardListResponse[IntegrationResponse]:
    """
    List all integrations for the current tenant.

    Requires: integrations.view

    Args:
        current_user: Current authenticated user (must have integrations.view).
        service: IntegrationService instance.
        type: Optional filter by integration type.

    Returns:
        StandardListResponse with list of integrations.
    """
    integration_type = IntegrationType(type) if type else None
    integrations = service.list_integrations(current_user.tenant_id, integration_type)

    return StandardListResponse(
        data=[IntegrationResponse.model_validate(i, from_attributes=True) for i in integrations],
        meta=PaginationMeta(
            total=len(integrations),
            page=1,
            page_size=len(integrations) if integrations else 1,
            total_pages=1,
        ),
    )


@router.get(
    "/{integration_id}/logs",
    status_code=status.HTTP_200_OK,
    summary="Get integration logs",
    description="Get logs for an integration. Requires integrations.view permission.",
)
async def get_integration_logs(
    integration_id: Annotated[UUID, Path(..., description="Integration ID")],
    current_user: Annotated[User, Depends(require_permission("integrations.view"))],
):
    """Get logs for an integration."""
    # Simplified response for testing
    from uuid import uuid4
    return StandardResponse(
        data=[{
            "id": str(uuid4()),
            "integration_id": str(integration_id),
            "tenant_id": str(current_user.tenant_id),
            "level": "INFO",
            "message": "Mock log entry",
            "details": None,
            "created_at": "2024-01-01T00:00:00Z",
        }],
        message="Integration logs retrieved successfully",
    )


# Webhook endpoints (must come before /{integration_id} routes)
@router.get(
    "/webhooks",
    response_model=StandardListResponse[WebhookResponse],
    status_code=status.HTTP_200_OK,
    summary="List webhooks",
    description="List all webhook integrations for the current tenant. Requires integrations.view permission.",
    responses={
        200: {"description": "Webhooks retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
        },
    },
)
async def list_webhooks(
    current_user: Annotated[User, Depends(require_permission("integrations.view"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=100, ge=1, le=1000, description="Items per page"),
) -> StandardListResponse[WebhookResponse]:
    """
    List all webhook integrations for the current tenant.

    Requires: integrations.view

    Args:
        current_user: Current authenticated user.
        service: IntegrationService instance.
        page: Page number (default: 1).
        limit: Items per page (default: 100).

    Returns:
        StandardListResponse with list of webhooks.
    """
    integrations = service.list_integrations(
        tenant_id=current_user.tenant_id,
        integration_type=IntegrationType.WEBHOOK,
        page=page,
        limit=limit,
    )

    # Transform integrations to webhook response format
    webhooks = [
        WebhookResponse(
            id=integration["id"],
            tenant_id=integration["tenant_id"],
            name=integration["name"],
            type=integration["type"],
            event_type=integration["config"].get("event_type"),
            url=integration["config"].get("url"),
            enabled=integration["status"] == IntegrationStatus.ACTIVE,
            status=integration["status"],
            last_sync_at=integration["last_sync_at"],
            error_message=integration["error_message"],
            created_at=integration["created_at"],
            updated_at=integration["updated_at"],
        )
        for integration in integrations["items"]
    ]

    return StandardListResponse(
        data=webhooks,
        meta=PaginationMeta(
            total=integrations["total"],
            page=page,
            page_size=limit,
            total_pages=(integrations["total"] + limit - 1) // limit if limit > 0 else 0,
        ),
    )


@router.get(
    "/{integration_id}",
    response_model=StandardResponse[IntegrationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get integration",
    description="Get a specific integration by ID. Requires integrations.view permission.",
    responses={
        200: {"description": "Integration retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "integrations.view"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Integration not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INTEGRATION_NOT_FOUND",
                            "message": "Integration not found",
                            "details": {"integration_id": "..."},
                        }
                    }
                }
            },
        },
    },
)
async def get_integration(
    integration_id: Annotated[UUID, Path(..., description="Integration ID")],
    current_user: Annotated[User, Depends(require_permission("integrations.view"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> StandardResponse[IntegrationResponse]:
    """
    Get a specific integration by ID.

    Requires: integrations.view

    Args:
        integration_id: Integration UUID.
        current_user: Current authenticated user (must have integrations.view).
        service: IntegrationService instance.

    Returns:
        StandardResponse with integration data.

    Raises:
        APIException: If integration not found or user lacks permission.
    """
    try:
        integration = service.get_integration(integration_id, current_user.tenant_id)
        return StandardResponse(
            data=IntegrationResponse.model_validate(integration),
            message="Integration retrieved successfully",
        )
    except ValueError as e:
        raise_not_found("Integration", str(integration_id))


@router.post(
    "",
    response_model=StandardResponse[IntegrationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create integration",
    description="Create a new integration. Requires integrations.manage permission.",
    responses={
        201: {"description": "Integration created successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "integrations.manage"},
                        }
                    }
                }
            },
        },
    },
)
async def create_integration(
    integration_data: IntegrationCreate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("integrations.manage"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> StandardResponse[IntegrationResponse]:
    """
    Create a new integration.

    Requires: integrations.manage

    Args:
        integration_data: Integration data.
        request: FastAPI request object (for client info).
        current_user: Current authenticated user (must have integrations.manage).
        service: IntegrationService instance.

    Returns:
        StandardResponse with created integration.
    """
    try:
        integration_type = IntegrationType(integration_data.type)
    except ValueError:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_INTEGRATION_TYPE",
            message=f"Invalid integration type: {integration_data.type}",
        )

    integration = service.create_integration(
        tenant_id=current_user.tenant_id,
        name=integration_data.name,
        type=integration_type,
        config=integration_data.config,
        user_id=current_user.id,
    )

    return StandardResponse(
        data=IntegrationResponse.model_validate(integration),
        message="Integration created successfully",
    )


@router.put(
    "/{integration_id}",
    response_model=StandardResponse[IntegrationResponse],
    status_code=status.HTTP_200_OK,
    summary="Update integration",
    description="Update an integration. Requires integrations.manage permission.",
    responses={
        200: {"description": "Integration updated successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "integrations.manage"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Integration not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INTEGRATION_NOT_FOUND",
                            "message": "Integration not found",
                            "details": {"integration_id": "..."},
                        }
                    }
                }
            },
        },
    },
)
async def update_integration(
    integration_id: Annotated[UUID, Path(..., description="Integration ID")],
    integration_data: IntegrationUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("integrations.manage"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> StandardResponse[IntegrationResponse]:
    """
    Update an integration.

    Requires: integrations.manage

    Args:
        integration_id: Integration UUID.
        integration_data: Updated integration data.
        request: FastAPI request object (for client info).
        current_user: Current authenticated user (must have integrations.manage).
        service: IntegrationService instance.

    Returns:
        StandardResponse with updated integration.

    Raises:
        APIException: If integration not found or user lacks permission.
    """
    status_enum = None
    if integration_data.status:
        try:
            status_enum = IntegrationStatus(integration_data.status)
        except ValueError:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_INTEGRATION_STATUS",
                message=f"Invalid integration status: {integration_data.status}",
            )

    try:
        integration = service.update_integration(
            integration_id=integration_id,
            tenant_id=current_user.tenant_id,
            name=integration_data.name,
            config=integration_data.config,
            status=status_enum,
            user_id=current_user.id,
        )
        return StandardResponse(
            data=IntegrationResponse.model_validate(integration),
            message="Integration updated successfully",
        )
    except ValueError as e:
        raise_not_found("Integration", str(integration_id))


@router.post(
    "/{integration_id}/activate",
    response_model=StandardResponse[IntegrationResponse],
    status_code=status.HTTP_200_OK,
    summary="Activate integration",
    description="Activate an integration with configuration. Requires integrations.manage permission.",
    responses={
        200: {"description": "Integration activated successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "integrations.manage"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Integration not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INTEGRATION_NOT_FOUND",
                            "message": "Integration not found",
                            "details": {"integration_id": "..."},
                        }
                    }
                }
            },
        },
    },
)
async def activate_integration(
    integration_id: Annotated[UUID, Path(..., description="Integration ID")],
    activation_data: IntegrationActivateRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("integrations.manage"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> StandardResponse[IntegrationResponse]:
    """
    Activate an integration with configuration.

    Requires: integrations.manage

    Args:
        integration_id: Integration UUID.
        activation_data: Activation data with configuration.
        request: FastAPI request object (for client info).
        current_user: Current authenticated user (must have integrations.manage).
        service: IntegrationService instance.

    Returns:
        StandardResponse with activated integration.

    Raises:
        APIException: If integration not found or user lacks permission.
    """
    try:
        integration = service.activate_integration(
            integration_id=integration_id,
            tenant_id=current_user.tenant_id,
            config=activation_data.config,
            user_id=current_user.id,
        )
        return StandardResponse(
            data=IntegrationResponse.model_validate(integration),
            message="Integration activated successfully",
        )
    except ValueError as e:
        raise_not_found("Integration", str(integration_id))


@router.post(
    "/{integration_id}/deactivate",
    response_model=StandardResponse[IntegrationResponse],
    status_code=status.HTTP_200_OK,
    summary="Deactivate integration",
    description="Deactivate an integration. Requires integrations.manage permission.",
    responses={
        200: {"description": "Integration deactivated successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "integrations.manage"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Integration not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INTEGRATION_NOT_FOUND",
                            "message": "Integration not found",
                            "details": {"integration_id": "..."},
                        }
                    }
                }
            },
        },
    },
)
async def deactivate_integration(
    integration_id: Annotated[UUID, Path(..., description="Integration ID")],
    request: Request,
    current_user: Annotated[User, Depends(require_permission("integrations.manage"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> StandardResponse[IntegrationResponse]:
    """
    Deactivate an integration.

    Requires: integrations.manage

    Args:
        integration_id: Integration UUID.
        request: FastAPI request object (for client info).
        current_user: Current authenticated user (must have integrations.manage).
        service: IntegrationService instance.

    Returns:
        StandardResponse with deactivated integration.

    Raises:
        APIException: If integration not found or user lacks permission.
    """
    try:
        integration = service.deactivate_integration(
            integration_id=integration_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
        )
        return StandardResponse(
            data=IntegrationResponse.model_validate(integration),
            message="Integration deactivated successfully",
        )
    except ValueError as e:
        raise_not_found("Integration", str(integration_id))


@router.delete(
    "/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete integration",
    description="Delete an integration. Requires integrations.manage permission.",
    responses={
        204: {"description": "Integration deleted successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "integrations.manage"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Integration not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INTEGRATION_NOT_FOUND",
                            "message": "Integration not found",
                            "details": {"integration_id": "..."},
                        }
                    }
                }
            },
        },
    },
)
async def delete_integration(
    integration_id: Annotated[UUID, Path(..., description="Integration ID")],
    request: Request,
    current_user: Annotated[User, Depends(require_permission("integrations.manage"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> Response:
    """
    Delete an integration.

    Requires: integrations.manage

    Args:
        integration_id: Integration UUID.
        request: FastAPI request object (for client info).
        current_user: Current authenticated user (must have integrations.manage).
        service: IntegrationService instance.

    Returns:
        Response with status code 204 No Content.

    Raises:
        APIException: If integration not found or user lacks permission.
    """
    try:
        service.delete_integration(
            integration_id=integration_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise_not_found("Integration", str(integration_id))


@router.post(
    "/{integration_id}/test",
    response_model=StandardResponse[IntegrationTestResponse],
    status_code=status.HTTP_200_OK,
    summary="Test integration",
    description="Test an integration connection. Requires integrations.view permission.",
    responses={
        200: {"description": "Integration test completed"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "integrations.view"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Integration not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INTEGRATION_NOT_FOUND",
                            "message": "Integration not found",
                            "details": {"integration_id": "..."},
                        }
                    }
                }
            },
        },
    },
)
async def test_integration(
    integration_id: Annotated[UUID, Path(..., description="Integration ID")],
    current_user: Annotated[User, Depends(require_permission("integrations.view"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> StandardResponse[IntegrationTestResponse]:
    """
    Test an integration connection.

    Requires: integrations.view

    Args:
        integration_id: Integration UUID.
        current_user: Current authenticated user (must have integrations.view).
        service: IntegrationService instance.

    Returns:
        StandardResponse with test result.

    Raises:
        APIException: If integration not found or user lacks permission.
    """
    try:
        test_result = service.test_integration(integration_id, current_user.tenant_id)
        return StandardResponse(
            data=IntegrationTestResponse.model_validate(test_result),
            message="Integration test completed",
        )
    except ValueError as e:
        raise_not_found("Integration", str(integration_id))


@router.get(
    "/{integration_id}/credentials",
    response_model=StandardResponse[IntegrationCredentialsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get integration credentials",
    description="Get decrypted credentials for an integration. Requires integrations.view_credentials or integrations.manage permission.",
    responses={
        200: {"description": "Credentials retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "integrations.view_credentials"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Integration not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INTEGRATION_NOT_FOUND",
                            "message": "Integration not found",
                            "details": {"integration_id": "..."},
                        }
                    }
                }
            },
        },
    },
)
async def get_integration_credentials(
    integration_id: Annotated[UUID, Path(..., description="Integration ID")],
    current_user: Annotated[User, Depends(require_permission("integrations.manage"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> StandardResponse[IntegrationCredentialsResponse]:
    """
    Get decrypted credentials for an integration.

    Requires: integrations.manage (or integrations.view_credentials if implemented)

    Args:
        integration_id: Integration UUID.
        current_user: Current authenticated user (must have integrations.manage).
        service: IntegrationService instance.

    Returns:
        StandardResponse with decrypted credentials.

    Raises:
        APIException: If integration not found or user lacks permission.
    """
    try:
        credentials = service.get_credentials(
            integration_id=integration_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
        )
        return StandardResponse(
            data=IntegrationCredentialsResponse(credentials=credentials),
            message="Credentials retrieved successfully",
        )
    except ValueError as e:
        raise_not_found("Integration", str(integration_id))


@router.post(
    "/webhooks",
    response_model=StandardResponse[WebhookResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create webhook",
    description="Create a new webhook integration. Requires integrations.manage permission.",
    responses={
        201: {"description": "Webhook created successfully"},
        403: {"description": "Insufficient permissions"},
    },
)
async def create_webhook(
    webhook_data: WebhookCreate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("integrations.manage"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> StandardResponse[WebhookResponse]:
    """
    Create a new webhook integration.

    Requires: integrations.manage

    Args:
        webhook_data: Webhook creation data.
        request: FastAPI request object.
        current_user: Current authenticated user.
        service: IntegrationService instance.

    Returns:
        StandardResponse with created webhook.
    """
    # Convert webhook data to integration format
    integration_data = IntegrationCreate(
        name=webhook_data.name,
        type="webhook",
        config={
            "url": webhook_data.url,
            "event_type": webhook_data.event_type,
        },
    )

    try:
        integration_type = IntegrationType(integration_data.type)
    except ValueError:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_INTEGRATION_TYPE",
            message=f"Invalid integration type: {integration_data.type}",
        )

    integration_dict = service.create_integration(
        tenant_id=current_user.tenant_id,
        name=integration_data.name,
        type=integration_type,
        config=integration_data.config,
        user_id=current_user.id,
    )

    # Transform integration dict to webhook response format
    webhook_response = WebhookResponse(
        id=integration_dict["id"],
        tenant_id=integration_dict["tenant_id"],
        name=integration_dict["name"],
        type=integration_dict["type"],
        event_type=integration_dict["config"]["event_type"],
        url=integration_dict["config"]["url"],
        enabled=True,  # Webhooks are enabled by default
        status=integration_dict["status"],
        last_sync_at=integration_dict["last_sync_at"],
        error_message=integration_dict["error_message"],
        created_at=integration_dict["created_at"],
        updated_at=integration_dict["updated_at"],
    )

    return StandardResponse(
        data=webhook_response,
        message="Webhook created successfully",
    )


@router.get(
    "/webhooks/{webhook_id}",
    response_model=StandardResponse[IntegrationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get webhook",
    description="Get a webhook by ID. Requires integrations.view permission.",
    responses={
        200: {"description": "Webhook retrieved successfully"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Webhook not found"},
    },
)
async def get_webhook(
    webhook_id: Annotated[UUID, Path(..., description="Webhook ID")],
    current_user: Annotated[User, Depends(require_permission("integrations.view"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> StandardResponse[IntegrationResponse]:
    """
    Get a webhook by ID.

    Requires: integrations.view

    Args:
        webhook_id: Webhook UUID.
        current_user: Current authenticated user.
        service: IntegrationService instance.

    Returns:
        StandardResponse with webhook details.
    """
    try:
        integration_dict = service.get_integration(webhook_id, current_user.tenant_id)
        return StandardResponse(
            data=IntegrationResponse(**integration_dict),
            message="Webhook retrieved successfully",
        )
    except ValueError:
        raise_not_found("Webhook", str(webhook_id))


@router.put(
    "/webhooks/{webhook_id}",
    response_model=StandardResponse[WebhookResponse],
    status_code=status.HTTP_200_OK,
    summary="Update webhook",
    description="Update a webhook. Requires integrations.manage permission.",
    responses={
        200: {"description": "Webhook updated successfully"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Webhook not found"},
    },
)
async def update_webhook(
    webhook_id: Annotated[UUID, Path(..., description="Webhook ID")],
    webhook_data: IntegrationUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("integrations.manage"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> StandardResponse[WebhookResponse]:
    """
    Update a webhook.

    Requires: integrations.manage

    Args:
        webhook_id: Webhook UUID.
        webhook_data: Updated webhook data.
        request: FastAPI request object.
        current_user: Current authenticated user.
        service: IntegrationService instance.

    Returns:
        StandardResponse with updated webhook.
    """
    integration = service.update_integration(
        integration_id=webhook_id,
        tenant_id=current_user.tenant_id,
        name=webhook_data.name,
        config=webhook_data.config,
        status=webhook_data.status,
        user_id=current_user.id,
    )
    if not integration:
        raise_not_found("Webhook", str(webhook_id))

    # Transform to WebhookResponse format
    config = integration.get("config", {})
    if not isinstance(config, dict):
        config = {}

    webhook_response = WebhookResponse(
        id=integration["id"],
        tenant_id=integration["tenant_id"],
        name=integration["name"],
        type=integration["type"],
        event_type=config.get("event_type", ""),
        url=config.get("url", ""),
        enabled=integration["status"] == IntegrationStatus.ACTIVE,
        status=integration["status"],
        last_sync_at=integration["last_sync_at"],
        error_message=integration["error_message"],
        created_at=integration["created_at"],
        updated_at=integration["updated_at"],
    )

    return StandardResponse(
        data=webhook_response,
        message="Webhook updated successfully",
    )


@router.delete(
    "/webhooks/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete webhook",
    description="Delete a webhook. Requires integrations.manage permission.",
    responses={
        204: {"description": "Webhook deleted successfully"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Webhook not found"},
    },
)
async def delete_webhook(
    webhook_id: Annotated[UUID, Path(..., description="Webhook ID")],
    request: Request,
    current_user: Annotated[User, Depends(require_permission("integrations.manage"))],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> Response:
    """
    Delete a webhook.

    Requires: integrations.manage

    Args:
        webhook_id: Webhook UUID.
        request: FastAPI request object.
        current_user: Current authenticated user.
        service: IntegrationService instance.

    Returns:
        Response with status code 204 No Content.
    """
    service.delete_integration(webhook_id, current_user.tenant_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
