"""Authentication router for login, refresh, logout, and user info."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user, require_permission
from app.core.auth.rate_limit import (
    check_login_rate_limit,
    create_rate_limit_exception,
    record_login_attempt,
)
from app.core.db.deps import get_db
from app.core.exceptions import (
    raise_bad_request,
    raise_forbidden,
    raise_internal_server_error,
    raise_not_found,
    raise_unauthorized,
)
from app.core.logging import (
    create_audit_log_entry,
    get_client_info,
    log_auth_failure,
    log_auth_success,
    log_logout,
    log_permission_change,
    log_rate_limit_exceeded,
)
from app.models.user import User
from app.schemas.audit import AuditLogListResponse
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshTokenRequest,
    RoleAssignRequest,
    RoleListResponse,
    RoleResponse,
    RoleWithPermissionsResponse,
    TokenResponse,
    UserMeResponse,
)
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.permission import (
    DelegatedPermissionListResponse,
    DelegatedPermissionResponse,
    PermissionGrantRequest,
    RevokePermissionResponse,
)
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.permission_service import PermissionService

router = APIRouter()


@router.post(
    "/login",
    response_model=StandardResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
)
async def login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[TokenResponse]:
    """
    Authenticate user and return access and refresh tokens.

    Security:
    - Rate limiting: 5 attempts per minute per IP
    - Does not reveal if user exists (generic error message)
    - Returns both access and refresh tokens on success

    Args:
        login_data: Login credentials (email, password).
        request: FastAPI request object (for IP address).
        db: Database session.

    Returns:
        TokenResponse with access_token and refresh_token.

    Raises:
        HTTPException: If credentials are invalid or rate limit exceeded.
    """
    import logging
    logger = logging.getLogger("app")
    logger.debug(f"[LOGIN] Endpoint called for email={login_data.email}")

    # Rate limiting check (only counts failed attempts)
    client_ip = request.client.host if request.client else "unknown"
    logger.debug(f"[LOGIN] Client IP: {client_ip}")

    # Check rate limit BEFORE authentication (only counts previous failed attempts)
    if not check_login_rate_limit(client_ip, max_attempts=5, window_minutes=1):
        log_rate_limit_exceeded(client_ip)
        raise create_rate_limit_exception()

    # Authenticate user
    logger.debug("[LOGIN] Step 0: Authenticating user")
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(login_data.email, login_data.password)
    logger.debug(f"[LOGIN] Step 0: Authentication completed, user={user is not None}")

    # Generic error message (does not reveal if user exists)
    if not user:
        logger.debug("[LOGIN] Step 0.1: User not found or invalid credentials")
        # This is a FAILED attempt - record it for rate limiting
        record_login_attempt(client_ip)
        log_auth_failure(login_data.email, "invalid_credentials", client_ip)
        raise_unauthorized(
            code="AUTH_INVALID_CREDENTIALS",
            message="Invalid credentials",
        )

    logger.debug(f"[LOGIN] Step 0.2: User authenticated successfully, user_id={user.id}")

    # Successful login - DO NOT record attempt
    # Successful logins should not count towards rate limiting

    # Log successful login (auth_service already logs, but we add IP here)
    try:
        logger.debug("[LOGIN] Step 0.3: Logging auth success")
        log_auth_success(str(user.id), login_data.email, str(user.tenant_id), client_ip)
        logger.debug("[LOGIN] Step 0.3: Auth success logged")
    except Exception as e:
        import logging
        logger = logging.getLogger("app")
        logger.warning(f"Failed to log auth success for user {user.id}: {e}", exc_info=True)
        # Continue even if logging fails

    logger.debug("[LOGIN] Step 0.4: About to create tokens")

    # Create tokens
    try:
        import logging
        # Use the configured app logger from app.core.logging
        logger = logging.getLogger("app")
        logger.debug(f"[LOGIN] Creating tokens for user {user.id}, email={login_data.email}")

        logger.debug(f"[LOGIN] Step 1: Creating access token for user {user.id}")
        logger.debug(f"[LOGIN] Step 1.1: Getting user roles for user {user.id}")
        access_token = auth_service.create_access_token_for_user(user)
        logger.debug("[LOGIN] Step 1: Access token created successfully")

        logger.debug(f"[LOGIN] Step 2: Creating refresh token for user {user.id}, remember_me={login_data.remember_me}")
        refresh_token = auth_service.create_refresh_token_for_user(user, remember_me=login_data.remember_me)
        logger.debug("[LOGIN] Step 2: Refresh token created successfully")

        logger.debug(f"[LOGIN] Tokens created successfully for user {user.id}")
    except Exception as e:
        # Log the error for debugging
        import logging

        from app.core.config_file import get_settings
        logger = logging.getLogger("app")
        settings = get_settings()
        logger.error(f"[LOGIN] Error creating tokens for user {user.id}: {e}", exc_info=True)
        raise_internal_server_error(
            code="TOKEN_CREATION_ERROR",
            message="Failed to create authentication tokens",
            details={"error": str(e)} if settings.DEBUG else None,
        )

    # Calculate cookie max_age based on remember_me
    from app.core.config_file import get_settings
    settings = get_settings()
    max_age_days = settings.REFRESH_TOKEN_REMEMBER_ME_DAYS if login_data.remember_me else settings.REFRESH_TOKEN_EXPIRE_DAYS
    max_age_seconds = max_age_days * 24 * 60 * 60

    # Set httpOnly cookie for refresh token
    cookie_secure = settings.COOKIE_SECURE if settings.ENV == "prod" else False
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=cookie_secure,
        samesite=settings.COOKIE_SAMESITE,
        max_age=max_age_seconds,
        domain=settings.COOKIE_DOMAIN if settings.COOKIE_DOMAIN else None,
    )

    return StandardResponse(
        data=TokenResponse(
            access_token=access_token,
            token_type="bearer",
            refresh_token=refresh_token,  # Also in response for compatibility
        ),
    )


@router.post(
    "/refresh",
    response_model=StandardResponse[AccessTokenResponse],
    status_code=status.HTTP_200_OK,
)
async def refresh_token(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    refresh_data: RefreshTokenRequest | None = Body(None),
) -> StandardResponse[AccessTokenResponse]:
    """
    Refresh an access token using a valid refresh token.

    Reads refresh token from cookie first, falls back to request body if not found.

    Args:
        request: FastAPI request object (for reading cookies).
        response: FastAPI response object (for setting cookies).
        refresh_data: Refresh token request (optional, used as fallback).
        db: Database session.

    Returns:
        AccessTokenResponse with new access_token.

    Raises:
        HTTPException: If refresh token is invalid, expired, or revoked.
    """
    # Try to get refresh token from cookie first
    refresh_token = request.cookies.get("refresh_token")

    # Fallback to request body if no cookie
    if not refresh_token:
        if not refresh_data or not refresh_data.refresh_token:
            raise_unauthorized(
                code="AUTH_REFRESH_TOKEN_INVALID",
                message="Refresh token not found",
            )
        refresh_token = refresh_data.refresh_token

    auth_service = AuthService(db)
    refresh_result = auth_service.refresh_access_token(refresh_token)

    if not refresh_result:
        raise_unauthorized(
            code="AUTH_REFRESH_TOKEN_INVALID",
            message="Invalid or expired refresh token",
        )
    access_token, new_refresh_token, refresh_expires_at = refresh_result

    # Update cookie with same settings (refresh token rotation could be added here)
    from app.core.config_file import get_settings
    settings = get_settings()
    cookie_secure = settings.COOKIE_SECURE if settings.ENV == "prod" else False

    # Use the refresh token's remaining lifetime for cookie max_age
    max_age_seconds = max(
        int((refresh_expires_at - datetime.now(UTC)).total_seconds()),
        0,
    )

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=cookie_secure,
        samesite=settings.COOKIE_SAMESITE,
        max_age=max_age_seconds,
        domain=settings.COOKIE_DOMAIN if settings.COOKIE_DOMAIN else None,
    )

    return StandardResponse(
        data=AccessTokenResponse(access_token=access_token, token_type="bearer"),
    )


@router.post("/logout", response_model=StandardResponse[dict[str, str]], status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    refresh_data: RefreshTokenRequest | None = Body(None),
) -> StandardResponse[dict[str, str]]:
    """
    Logout user by revoking refresh token.

    Reads refresh token from cookie first, falls back to request body if not found.

    Args:
        request: FastAPI request object (for IP address and cookies).
        response: FastAPI response object (for deleting cookie).
        refresh_data: Refresh token to revoke (optional, used as fallback).
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        Success message.

    Raises:
        HTTPException: If refresh token is invalid.
    """
    # Try to get refresh token from cookie first
    refresh_token = request.cookies.get("refresh_token")

    # Fallback to request body if no cookie
    if not refresh_token:
        if not refresh_data or not refresh_data.refresh_token:
            raise_unauthorized(
                code="AUTH_REFRESH_TOKEN_INVALID",
                message="Refresh token not found",
            )
        refresh_token = refresh_data.refresh_token

    auth_service = AuthService(db)
    success = auth_service.revoke_refresh_token(
        refresh_token, current_user.id
    )

    if not success:
        raise_unauthorized(
            code="AUTH_REFRESH_TOKEN_INVALID",
            message="Invalid refresh token",
        )

    # Delete cookie
    from app.core.config_file import get_settings
    settings = get_settings()
    response.delete_cookie(
        key="refresh_token",
        domain=settings.COOKIE_DOMAIN if settings.COOKIE_DOMAIN else None,
        samesite=settings.COOKIE_SAMESITE,
    )

    # Log logout
    client_ip = request.client.host if request.client else "unknown"
    log_logout(str(current_user.id), client_ip)

    return StandardResponse(data={"message": "Logged out successfully"})


@router.get("/me", response_model=StandardResponse[UserMeResponse], status_code=status.HTTP_200_OK)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[UserMeResponse]:
    """
    Get current authenticated user information with roles and permissions.

    Args:
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        StandardResponse with UserMeResponse containing user info, roles, and permissions.
    """
    auth_service = AuthService(db)
    roles = auth_service.get_user_roles(current_user.id)
    permissions = auth_service.get_user_permissions(current_user.id)

    # Get tenant name if tenant exists
    tenant_name = current_user.tenant.name if current_user.tenant else None

    return StandardResponse(
        data=UserMeResponse(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
            tenant_id=current_user.tenant_id,
            tenant_name=tenant_name,
            roles=roles,
            permissions=permissions,
        )
    )


@router.get(
    "/encryption-secret",
    response_model=StandardResponse[dict[str, str | None]],
    status_code=status.HTTP_200_OK,
    summary="Get encryption secret for client-side encryption",
    description="Get a tenant-specific encryption secret for client-side data encryption. The secret expires after 24 hours. Requires authentication.",
    responses={
        200: {"description": "Encryption secret retrieved successfully"},
        401: {"description": "Unauthorized"},
    },
)
async def get_encryption_secret(
    current_user: Annotated[User, Depends(get_current_user)],
) -> StandardResponse[dict[str, str | None]]:
    """
    Get encryption secret for client-side encryption.

    The secret is tenant-specific and should be used for encrypting sensitive
    data in localStorage. The secret expires after 24 hours and should be
    refreshed periodically.

    Security:
    - Secret is tenant-specific (derived from tenant_id)
    - Expires after 24 hours
    - Should be stored in memory only (not in localStorage)
    - Should be refreshed on login and periodically

    Args:
        current_user: Current authenticated user.

    Returns:
        StandardResponse with encryption secret and expiration time.
    """
    import hashlib
    import hmac
    from datetime import datetime, timedelta

    from app.core.config_file import get_settings

    # Get settings (contains SECRET_KEY used for JWT)
    settings = get_settings()
    secret_key = settings.SECRET_KEY

    # Generate tenant-specific secret
    # Combine tenant_id with app secret for uniqueness
    tenant_secret_key = f"{current_user.tenant_id}:{secret_key}"

    # Generate a deterministic but secure secret using HMAC
    # This ensures the same tenant always gets the same secret (until expiration)
    secret_hash = hmac.new(
        secret_key.encode(),
        tenant_secret_key.encode(),
        hashlib.sha256
    ).hexdigest()

    # Use first 32 characters as secret (sufficient for encryption)
    encryption_secret = secret_hash[:32]

    # Set expiration to 24 hours from now
    expires_at = datetime.utcnow() + timedelta(hours=24)

    return StandardResponse(
        data={
            "secret": encryption_secret,
            "expires_at": expires_at.isoformat(),
        },
        message="Encryption secret retrieved successfully",
    )


@router.post(
    "/modules/{module}/permissions",
    response_model=StandardResponse[DelegatedPermissionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Grant a delegated permission",
    description="Grant a delegated permission to a user. Requires {module}.manage_users permission.",
    responses={
        201: {"description": "Permission granted successfully"},
        400: {
            "description": "Invalid permission or validation error",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INVALID_PERMISSION",
                            "message": "Cannot delegate permission '*.manage_users'",
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
                            "code": "PERMISSION_DENIED",
                            "message": "User does not have permission 'inventory.manage_users' to grant permissions",
                            "details": None,
                        }
                    }
                }
            },
        },
        409: {
            "description": "Permission already exists",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "PERMISSION_ALREADY_EXISTS",
                            "message": "Permission 'inventory.edit' already granted to this user by you",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def grant_permission(
    module: str,
    permission_data: PermissionGrantRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[DelegatedPermissionResponse]:
    """
    Grant a delegated permission to a user.

    Requires: {module}.manage_users

    Args:
        module: Module name (e.g., "inventory", "products").
        permission_data: Permission grant request (user_id, permission, expires_at).
        current_user: Current authenticated user (must have {module}.manage_users).
        db: Database session.

    Returns:
        DelegatedPermissionResponse with granted permission details.

    Raises:
        HTTPException: If user lacks permission or validation fails.
    """
    permission_service = PermissionService(db)

    # Verificar que el permiso pertenece al módulo
    if not permission_data.permission.startswith(f"{module}."):
        raise_bad_request(
            code="INVALID_PERMISSION",
            message=f"Permission '{permission_data.permission}' does not belong to module '{module}'",
        )

    delegated_permission = permission_service.grant_permission(
        user_id=permission_data.user_id,
        module=module,
        permission=permission_data.permission,
        expires_at=permission_data.expires_at,
        granted_by=current_user.id,
    )

    return StandardResponse(
        data=DelegatedPermissionResponse(
        id=delegated_permission.id,
        user_id=delegated_permission.user_id,
        granted_by=delegated_permission.granted_by,
        module=delegated_permission.module,
        permission=delegated_permission.permission,
        expires_at=delegated_permission.expires_at,
        created_at=delegated_permission.created_at,
        revoked_at=delegated_permission.revoked_at,
        is_active=delegated_permission.is_active,
        ),
        message="Permission granted successfully",
    )


@router.delete(
    "/modules/{module}/permissions/{permission_id}",
    response_model=StandardResponse[RevokePermissionResponse],
    status_code=status.HTTP_200_OK,
    summary="Revoke a delegated permission",
    description="Revoke a delegated permission. Requires being the granter OR having auth.manage_users.",
    responses={
        200: {"description": "Permission revoked successfully"},
        400: {
            "description": "Invalid request",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "PERMISSION_ALREADY_REVOKED",
                            "message": "Permission is already revoked",
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
                            "code": "PERMISSION_DENIED",
                            "message": "You can only revoke permissions you granted",
                            "details": None,
                        }
                    }
                }
            },
        },
        404: {
            "description": "Permission not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "PERMISSION_NOT_FOUND",
                            "message": "Permission not found",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def revoke_permission(
    module: str,
    permission_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RevokePermissionResponse:
    """
    Revoke a delegated permission.

    Requires: Be the granter OR have auth.manage_users

    Args:
        module: Module name (for validation).
        permission_id: Permission UUID to revoke.
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        RevokePermissionResponse with success message.

    Raises:
        HTTPException: If permission not found or user lacks permission.
    """
    permission_service = PermissionService(db)

    # Verificar que el permiso pertenece al módulo
    from app.repositories.permission_repository import PermissionRepository

    repo = PermissionRepository(db)
    permission = repo.get_delegated_permission_by_id(permission_id)
    if permission and permission.module != module:
        raise_bad_request(
            code="INVALID_MODULE",
            message=f"Permission does not belong to module '{module}'",
        )

    permission_service.revoke_permission(permission_id, current_user.id)

    return RevokePermissionResponse(
        message="Permission revoked successfully",
        revoked_count=1,
    )


@router.delete(
    "/users/{user_id}/permissions",
    response_model=StandardResponse[RevokePermissionResponse],
    status_code=status.HTTP_200_OK,
    summary="Revoke all delegated permissions of a user",
    description="Revoke ALL delegated permissions of a user. Requires auth.manage_users or owner/admin role.",
    responses={
        200: {"description": "Permissions revoked successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "PERMISSION_DENIED",
                            "message": "Only administrators or owners can revoke all permissions of a user",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def revoke_all_user_permissions(
    user_id: UUID,
    current_user: Annotated[User, Depends(require_permission("auth.manage_users"))],
    db: Annotated[Session, Depends(get_db)],
) -> RevokePermissionResponse:
    """
    Revoke ALL delegated permissions of a user.

    Requires: auth.manage_users or owner/admin role

    Args:
        user_id: User UUID whose permissions will be revoked.
        current_user: Current authenticated user (must be admin/owner).
        db: Database session.

    Returns:
        RevokePermissionResponse with number of permissions revoked.

    Raises:
        HTTPException: If user lacks permission.
    """
    permission_service = PermissionService(db)
    revoked_count = permission_service.revoke_all_user_permissions(
        user_id, current_user.id
    )

    return StandardResponse(
        data=RevokePermissionResponse(
        message=f"Revoked {revoked_count} permission(s) successfully",
        revoked_count=revoked_count,
        ),
        message="Permissions revoked successfully",
    )


@router.delete(
    "/users/{user_id}/permissions/{permission_id}",
    response_model=StandardResponse[RevokePermissionResponse],
    status_code=status.HTTP_200_OK,
    summary="Revoke a specific delegated permission (admin override)",
    description="Revoke a specific delegated permission. Admin override - can revoke any permission. Requires auth.manage_users or owner/admin role.",
    responses={
        200: {"description": "Permission revoked successfully"},
        400: {
            "description": "Invalid request",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INVALID_USER",
                            "message": "Permission does not belong to this user",
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
            "description": "Permission not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "PERMISSION_NOT_FOUND",
                            "message": "Permission not found",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def revoke_user_permission(
    user_id: UUID,
    permission_id: UUID,
    current_user: Annotated[User, Depends(require_permission("auth.manage_users"))],
    db: Annotated[Session, Depends(get_db)],
) -> RevokePermissionResponse:
    """
    Revoke a specific delegated permission (admin override).

    Requires: auth.manage_users or owner/admin role

    Args:
        user_id: User UUID (for validation).
        permission_id: Permission UUID to revoke.
        current_user: Current authenticated user (must be admin/owner).
        db: Database session.

    Returns:
        RevokePermissionResponse with success message.

    Raises:
        HTTPException: If permission not found or user lacks permission.
    """
    from app.repositories.permission_repository import PermissionRepository

    # Verificar que el permiso pertenece al usuario
    repo = PermissionRepository(db)
    permission = repo.get_delegated_permission_by_id(permission_id)
    if not permission:
        raise_not_found("Permission", str(permission_id))

    if permission.user_id != user_id:
        raise_bad_request(
            code="INVALID_USER",
            message="Permission does not belong to this user",
        )

    permission_service = PermissionService(db)
    permission_service.revoke_permission(permission_id, current_user.id)

    return StandardResponse(
        data=RevokePermissionResponse(
        message="Permission revoked successfully",
        revoked_count=1,
        ),
        message="Permission revoked successfully",
    )


@router.get(
    "/modules/{module}/permissions/{user_id}",
    response_model=DelegatedPermissionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List delegated permissions for a user in a module",
    description="List all delegated permissions (active and revoked) for a user in a specific module. Requires authentication.",
    responses={
        200: {"description": "List of permissions retrieved successfully"},
    },
)
async def get_user_module_permissions(
    module: str,
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DelegatedPermissionListResponse:
    """
    List delegated permissions for a user in a module.

    Requires: Authentication

    Args:
        module: Module name.
        user_id: User UUID.
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        DelegatedPermissionListResponse with list of permissions.
    """
    from app.repositories.permission_repository import PermissionRepository

    repo = PermissionRepository(db)
    permissions = repo.get_user_module_permissions(user_id, module)

    permission_responses = [
        DelegatedPermissionResponse(
            id=perm.id,
            user_id=perm.user_id,
            granted_by=perm.granted_by,
            module=perm.module,
            permission=perm.permission,
            expires_at=perm.expires_at,
            created_at=perm.created_at,
            revoked_at=perm.revoked_at,
            is_active=perm.is_active,
        )
        for perm in permissions
    ]

    return DelegatedPermissionListResponse(
        permissions=permission_responses,
        total=len(permission_responses),
    )


@router.get(
    "/roles",
    response_model=StandardListResponse[RoleWithPermissionsResponse],
    status_code=status.HTTP_200_OK,
    summary="List available global roles",
    description="List all available global roles with their permissions. Requires authentication.",
    responses={
        200: {"description": "List of roles retrieved successfully"},
    },
)
async def list_roles(
    current_user: Annotated[User, Depends(get_current_user)],
) -> StandardListResponse[RoleWithPermissionsResponse]:
    """
    List all available global roles.

    Requires: Authentication

    Args:
        current_user: Current authenticated user.

    Returns:
        StandardListResponse with available roles and their permissions.
    """
    from app.core.auth.permissions import ROLE_PERMISSIONS

    roles_data = [
        RoleWithPermissionsResponse(
            role=role,
            permissions=list(permissions),
        )
        for role, permissions in ROLE_PERMISSIONS.items()
    ]

    total = len(roles_data)
    page_size = max(total, 1)

    return StandardListResponse(
        data=roles_data,
        meta={
            "total": total,
            "page": 1,
            "page_size": page_size,
            "total_pages": 1,
        },
        message="Roles retrieved successfully",
    )


@router.get(
    "/roles/{user_id}",
    response_model=RoleListResponse,
    status_code=status.HTTP_200_OK,
    summary="List user roles",
    description="List all global roles assigned to a user. Requires auth.manage_users permission.",
    responses={
        200: {"description": "List of user roles retrieved successfully"},
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
async def get_user_roles(
    user_id: UUID,
    current_user: Annotated[User, Depends(require_permission("auth.manage_users"))],
    db: Annotated[Session, Depends(get_db)],
) -> RoleListResponse:
    """
    List all global roles assigned to a user.

    Requires: auth.manage_users

    Args:
        user_id: User UUID.
        current_user: Current authenticated user (must have auth.manage_users).
        db: Database session.

    Returns:
        RoleListResponse with list of roles.

    Raises:
        HTTPException: If user not found or lacks permission.
    """
    from app.models.user_role import UserRole
    from app.repositories.user_repository import UserRepository

    # Verify user exists and belongs to same tenant
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise_not_found("User", str(user_id))

    if user.tenant_id != current_user.tenant_id:
        raise_forbidden(
            code="AUTH_TENANT_MISMATCH",
            message="Cannot access user from different tenant",
        )

    # Get user roles
    roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()

    role_responses = [
        RoleResponse(
            role=role.role,
            granted_by=role.granted_by,
            created_at=role.created_at,
        )
        for role in roles
    ]

    return RoleListResponse(roles=role_responses, total=len(role_responses))


@router.post(
    "/roles/{user_id}",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign global role to user",
    description="Assign a global role to a user. Requires auth.manage_roles permission.",
    responses={
        201: {"description": "Role assigned successfully"},
        400: {
            "description": "Invalid request or role already assigned",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "ROLE_ALREADY_ASSIGNED",
                            "message": "Role 'admin' is already assigned to this user",
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
                            "details": {"required_permission": "auth.manage_roles"},
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
async def assign_role(
    user_id: UUID,
    role_data: RoleAssignRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("auth.manage_roles"))],
    db: Annotated[Session, Depends(get_db)],
) -> RoleResponse:
    """
    Assign a global role to a user.

    Requires: auth.manage_roles

    Args:
        user_id: User UUID.
        role_data: Role assignment request.
        current_user: Current authenticated user (must have auth.manage_roles).
        db: Database session.

    Returns:
        RoleResponse with assigned role details.

    Raises:
        HTTPException: If user not found, role already assigned, or validation fails.
    """
    from app.models.user_role import UserRole
    from app.repositories.user_repository import UserRepository

    # Verify user exists and belongs to same tenant
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise_not_found("User", str(user_id))

    if user.tenant_id != current_user.tenant_id:
        raise_forbidden(
            code="AUTH_TENANT_MISMATCH",
            message="Cannot access user from different tenant",
        )

    # Check if role already assigned
    existing_role = (
        db.query(UserRole)
        .filter(UserRole.user_id == user_id, UserRole.role == role_data.role)
        .first()
    )
    if existing_role:
        from app.core.exceptions import raise_conflict
        raise_conflict(
            code="ROLE_ALREADY_ASSIGNED",
            message=f"Role '{role_data.role}' is already assigned to this user",
        )

    # Create role assignment
    user_role = UserRole(
        user_id=user_id,
        role=role_data.role,
        granted_by=current_user.id,
    )
    db.add(user_role)
    db.commit()
    db.refresh(user_role)

    # Get client info for audit log
    ip_address, user_agent = get_client_info(request)

    # Log to console
    log_permission_change(
        user_id=str(current_user.id),
        action="assign_global_role",
        target_user_id=str(user_id),
        details={"role": role_data.role, "role_id": str(user_role.id)},
    )

    # Create audit log entry
    create_audit_log_entry(
        db=db,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        action="assign_global_role",
        resource_type="role",
        resource_id=user_role.id,
        details={"role": role_data.role, "target_user_id": str(user_id)},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return RoleResponse(
        role=user_role.role,
        granted_by=user_role.granted_by,
        created_at=user_role.created_at,
    )


@router.delete(
    "/roles/{user_id}/{role}",
    response_model=StandardResponse[dict[str, str]],
    status_code=status.HTTP_200_OK,
    summary="Remove global role from user",
    description="Remove a global role from a user. Requires auth.manage_roles permission.",
    responses={
        200: {"description": "Role removed successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "auth.manage_roles"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "User or role not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "ROLE_NOT_FOUND",
                            "message": "Role 'admin' is not assigned to this user",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def remove_role(
    user_id: UUID,
    role: str,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("auth.manage_roles"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict[str, str]]:
    """
    Remove a global role from a user.

    Requires: auth.manage_roles

    Args:
        user_id: User UUID.
        role: Role name to remove.
        current_user: Current authenticated user (must have auth.manage_roles).
        db: Database session.

    Returns:
        Dictionary with success message.

    Raises:
        HTTPException: If user not found, role not assigned, or lacks permission.
    """
    from app.core.auth.permissions import ROLE_PERMISSIONS
    from app.models.user_role import UserRole
    from app.repositories.user_repository import UserRepository

    # Validate role
    if role not in ROLE_PERMISSIONS:
        raise_bad_request(
            code="INVALID_ROLE",
            message=f"Invalid role '{role}'. Valid roles: {', '.join(ROLE_PERMISSIONS.keys())}",
        )

    # Verify user exists and belongs to same tenant
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise_not_found("User", str(user_id))

    if user.tenant_id != current_user.tenant_id:
        raise_forbidden(
            code="AUTH_TENANT_MISMATCH",
            message="Cannot access user from different tenant",
        )

    # Find and remove role
    user_role = (
        db.query(UserRole)
        .filter(UserRole.user_id == user_id, UserRole.role == role)
        .first()
    )
    if not user_role:
        raise_not_found("Role", f"{role} for user {user_id}")

    # Store role info before deletion for audit log
    original_granted_by = user_role.granted_by

    db.delete(user_role)
    db.commit()

    # Get client info for audit log
    ip_address, user_agent = get_client_info(request)

    # Log to console
    log_permission_change(
        user_id=str(current_user.id),
        action="remove_global_role",
        target_user_id=str(user_id),
        details={
            "role": role,
            "original_granted_by": str(original_granted_by) if original_granted_by else None,
        },
    )

    # Create audit log entry
    create_audit_log_entry(
        db=db,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        action="remove_global_role",
        resource_type="role",
        resource_id=None,  # Role already deleted
        details={
            "role": role,
            "target_user_id": str(user_id),
            "original_granted_by": str(original_granted_by) if original_granted_by else None,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return StandardResponse(data={"message": f"Role '{role}' removed successfully"})


@router.get(
    "/audit-logs",
    response_model=AuditLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get audit logs",
    description="Get audit logs with filters and pagination. Requires auth.view_audit permission.",
    responses={
        200: {"description": "Audit logs retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "auth.view_audit"},
                        }
                    }
                }
            },
        },
    },
)
async def get_audit_logs(
    current_user: Annotated[User, Depends(require_permission("auth.view_audit"))],
    db: Annotated[Session, Depends(get_db)],
    user_id: UUID | None = Query(None, description="Filter by user ID"),
    action: str | None = Query(None, description="Filter by action type"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    date_from: datetime | None = Query(None, description="Filter by start date (ISO format)"),
    date_to: datetime | None = Query(None, description="Filter by end date (ISO format)"),
    ip_address: str | None = Query(None, description="Filter by IP address (partial match)"),
    user_agent: str | None = Query(None, description="Filter by user agent (partial match)"),
    details_search: str | None = Query(None, description="Search in details JSON (partial match)"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> AuditLogListResponse:
    """
    Get audit logs with filters and pagination.

    Requires: auth.view_audit

    Args:
        current_user: Current authenticated user (must have auth.view_audit).
        db: Database session.
        user_id: Filter by user ID (optional).
        action: Filter by action type (optional).
        resource_type: Filter by resource type (optional).
        date_from: Filter by start date (optional).
        date_to: Filter by end date (optional).
        ip_address: Filter by IP address (partial match, optional).
        user_agent: Filter by user agent (partial match, optional).
        details_search: Search in details JSON (partial match, optional).
        page: Page number (default: 1).
        page_size: Page size (default: 20, max: 100).

    Returns:
        AuditLogListResponse with list of audit logs and pagination metadata.

    Raises:
        HTTPException: If user lacks permission.
    """
    audit_service = AuditService(db)
    skip = (page - 1) * page_size

    logs, total = audit_service.get_audit_logs(
        tenant_id=current_user.tenant_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        date_from=date_from,
        date_to=date_to,
        ip_address=ip_address,
        user_agent=user_agent,
        details_search=details_search,
        skip=skip,
        limit=page_size,
    )

    return AuditLogListResponse(
        data=logs,
        meta={
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        },
    )
