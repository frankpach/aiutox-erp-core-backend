"""Integration router for third-party service integrations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request, status
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
    IntegrationResponse,
    IntegrationTestResponse,
    IntegrationUpdate,
)

router = APIRouter()


def get_integration_service(
    db: Annotated[Session, Depends(get_db)],
) -> IntegrationService:
    """Dependency to get IntegrationService."""
    return IntegrationService(db)


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
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete integration",
    description="Delete an integration. Requires integrations.manage permission.",
    responses={
        200: {"description": "Integration deleted successfully"},
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
) -> StandardResponse[dict]:
    """
    Delete an integration.

    Requires: integrations.manage

    Args:
        integration_id: Integration UUID.
        request: FastAPI request object (for client info).
        current_user: Current authenticated user (must have integrations.manage).
        service: IntegrationService instance.

    Returns:
        StandardResponse with success message.

    Raises:
        APIException: If integration not found or user lacks permission.
    """
    try:
        service.delete_integration(
            integration_id=integration_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
        )
        return StandardResponse(
            data={"message": "Integration deleted successfully"},
            message="Integration deleted successfully",
        )
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
