"""User management router for CRUD operations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import (
    raise_bad_request,
    raise_forbidden,
    raise_not_found,
)
from app.core.logging import get_client_info
from app.models.user import User
from app.schemas.common import PaginationMeta, StandardListResponse, StandardResponse
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


@router.get(
    "",
    response_model=StandardListResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="List users",
    description="List all users in the current tenant. Requires auth.manage_users permission.",
    responses={
        200: {"description": "List of users retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "auth.manage_users"},
                        }
                    }
                }
            },
        },
    },
)
async def list_users(
    current_user: Annotated[User, Depends(require_permission("auth.manage_users"))],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[dict]:
    """
    List all users in the current tenant.

    Requires: auth.manage_users

    Args:
        current_user: Current authenticated user (must have auth.manage_users).
        db: Database session.
        page: Page number (default: 1).
        page_size: Page size (default: 20, max: 100).

    Returns:
        StandardListResponse with list of users and pagination metadata.

    Raises:
        APIException: If user lacks permission.
    """
    user_service = UserService(db)
    skip = (page - 1) * page_size
    users, total = user_service.list_users(
        tenant_id=current_user.tenant_id, skip=skip, limit=page_size
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Return user dicts directly (UserResponse has forward references that need model_rebuild)
    return StandardListResponse(
        data=users,
        meta=PaginationMeta(
            total=total, page=page, page_size=page_size, total_pages=total_pages
        ),
    )


@router.post(
    "",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create a new user. Requires auth.manage_users permission.",
    responses={
        201: {"description": "User created successfully"},
        400: {
            "description": "Invalid request or user already exists",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "USER_ALREADY_EXISTS",
                            "message": "User with email 'user@example.com' already exists",
                            "details": None,
                        }
                    }
                }
            },
        },
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "auth.manage_users"},
                        }
                    }
                }
            },
        },
    },
)
async def create_user(
    user_data: UserCreate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("auth.manage_users"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Create a new user.

    Requires: auth.manage_users

    Args:
        user_data: User creation data.
        current_user: Current authenticated user (must have auth.manage_users).
        db: Database session.

    Returns:
        StandardResponse with created user data.

    Raises:
        APIException: If user already exists or validation fails.
    """
    # Ensure user is created in the same tenant as current user
    if user_data.tenant_id != current_user.tenant_id:
        raise_forbidden(
            code="AUTH_TENANT_MISMATCH",
            message="Cannot create user in different tenant",
        )

    user_service = UserService(db)
    ip_address, user_agent = get_client_info(request)
    try:
        user_dict = user_service.create_user(
            user_data,
            created_by=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        user = user_service.get_user(user_dict["id"])
        return StandardResponse(data=user)
    except ValueError as e:
        raise_bad_request(code="USER_ALREADY_EXISTS", message=str(e))


@router.get(
    "/{user_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get user",
    description="Get user by ID. Requires auth.manage_users permission.",
    responses={
        200: {"description": "User retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "auth.manage_users"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "User not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "USER_NOT_FOUND",
                            "message": "User not found",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def get_user(
    user_id: str,
    current_user: Annotated[User, Depends(require_permission("auth.manage_users"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Get user by ID.

    Requires: auth.manage_users

    Args:
        user_id: User UUID.
        current_user: Current authenticated user (must have auth.manage_users).
        db: Database session.

    Returns:
        StandardResponse with user data.

    Raises:
        APIException: If user not found or lacks permission.
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise_bad_request(code="INVALID_UUID", message="Invalid user ID format")

    user_service = UserService(db)
    user = user_service.get_user(user_uuid)

    if not user:
        raise_not_found("User", user_id)

    # Verify tenant access
    if user["tenant_id"] != current_user.tenant_id:
        raise_forbidden(
            code="AUTH_TENANT_MISMATCH",
            message="Cannot access user from different tenant",
        )

    return StandardResponse(data=user)


@router.patch(
    "/{user_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Update user",
    description="Update user by ID. Requires auth.manage_users permission.",
    responses={
        200: {"description": "User updated successfully"},
        400: {
            "description": "Invalid request or user already exists",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "USER_ALREADY_EXISTS",
                            "message": "User with email 'user@example.com' already exists",
                            "details": None,
                        }
                    }
                }
            },
        },
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "auth.manage_users"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "User not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "USER_NOT_FOUND",
                            "message": "User not found",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("auth.manage_users"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Update user by ID.

    Requires: auth.manage_users

    Args:
        user_id: User UUID.
        user_data: User update data.
        current_user: Current authenticated user (must have auth.manage_users).
        db: Database session.

    Returns:
        StandardResponse with updated user data.

    Raises:
        APIException: If user not found, validation fails, or lacks permission.
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise_bad_request(code="INVALID_UUID", message="Invalid user ID format")

    user_service = UserService(db)
    existing_user = user_service.get_user(user_uuid)

    if not existing_user:
        raise_not_found("User", user_id)

    # Verify tenant access
    if existing_user["tenant_id"] != current_user.tenant_id:
        raise_forbidden(
            code="AUTH_TENANT_MISMATCH",
            message="Cannot access user from different tenant",
        )

    ip_address, user_agent = get_client_info(request)
    try:
        updated_user = user_service.update_user(
            user_uuid,
            user_data,
            updated_by=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if not updated_user:
            raise_not_found("User", user_id)
        return StandardResponse(data=updated_user)
    except ValueError as e:
        raise_bad_request(code="USER_ALREADY_EXISTS", message=str(e))


@router.delete(
    "/{user_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete user (soft delete)",
    description="Soft delete user by setting is_active=False. Requires auth.manage_users permission.",
    responses={
        200: {"description": "User deleted successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "auth.manage_users"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "User not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "USER_NOT_FOUND",
                            "message": "User not found",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def delete_user(
    user_id: str,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("auth.manage_users"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Soft delete user by setting is_active=False.

    Requires: auth.manage_users

    Args:
        user_id: User UUID.
        current_user: Current authenticated user (must have auth.manage_users).
        db: Database session.

    Returns:
        StandardResponse with success message.

    Raises:
        APIException: If user not found or lacks permission.
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise_bad_request(code="INVALID_UUID", message="Invalid user ID format")

    user_service = UserService(db)
    existing_user = user_service.get_user(user_uuid)

    if not existing_user:
        raise_not_found("User", user_id)

    # Verify tenant access
    if existing_user["tenant_id"] != current_user.tenant_id:
        raise_forbidden(
            code="AUTH_TENANT_MISMATCH",
            message="Cannot access user from different tenant",
        )

    ip_address, user_agent = get_client_info(request)
    success = user_service.delete_user(
        user_uuid,
        deactivated_by=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if not success:
        raise_not_found("User", user_id)

    return StandardResponse(data={"message": "User deleted successfully"})
