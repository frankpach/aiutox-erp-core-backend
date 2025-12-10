"""FastAPI dependencies for authentication and authorization."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.auth import decode_token
from app.core.db.deps import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    Get the current authenticated user from JWT token.

    Args:
        token: JWT access token from Authorization header.
        db: Database session.

    Returns:
        User object if token is valid and user exists.

    Raises:
        HTTPException: If token is invalid, expired, or user not found.
    """
    # Decode token
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_INVALID_TOKEN",
                    "message": "Invalid or expired token",
                    "details": None,
                }
            },
        )

    # Verify token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_INVALID_TOKEN",
                    "message": "Invalid token type",
                    "details": None,
                }
            },
        )

    # Get user ID from token
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_INVALID_TOKEN",
                    "message": "Token missing user ID",
                    "details": None,
                }
            },
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_INVALID_TOKEN",
                    "message": "Invalid user ID in token",
                    "details": None,
                }
            },
        )

    # Get tenant_id from token
    tenant_id_str = payload.get("tenant_id")
    if not tenant_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_INVALID_TOKEN",
                    "message": "Token missing tenant ID",
                    "details": None,
                }
            },
        )

    try:
        token_tenant_id = UUID(tenant_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_INVALID_TOKEN",
                    "message": "Invalid tenant ID in token",
                    "details": None,
                }
            },
        )

    # Get user from database
    user_repository = UserRepository(db)
    user = user_repository.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_USER_NOT_FOUND",
                    "message": "User not found",
                    "details": None,
                }
            },
        )

    # Verify tenant_id matches (multi-tenant security)
    if user.tenant_id != token_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "AUTH_TENANT_MISMATCH",
                    "message": "Token tenant does not match user tenant",
                    "details": None,
                }
            },
        )

    # Verify user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "AUTH_USER_INACTIVE",
                    "message": "User account is inactive",
                    "details": None,
                }
            },
        )

    return user


async def get_user_permissions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> set[str]:
    """
    Get effective permissions for the current user.

    Phase 2: Only global roles are considered.
    Phase 3+: Will include module roles and delegated permissions.

    Args:
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        Set of permission strings.
    """
    from app.services.permission_service import PermissionService

    permission_service = PermissionService(db)
    return permission_service.get_effective_permissions(current_user.id)


def verify_tenant_access(user: User, tenant_id: UUID) -> bool:
    """
    Verify that a user has access to a specific tenant.

    Args:
        user: User object.
        tenant_id: Tenant ID to verify.

    Returns:
        True if user belongs to the tenant, False otherwise.
    """
    return user.tenant_id == tenant_id


def require_permission(permission: str):
    """
    Dependency factory to require a specific permission.

    Usage:
        @router.get("/items")
        async def list_items(
            user: User = Depends(require_permission("inventory.view")),
            db: Session = Depends(get_db)
        ):
            ...

    Args:
        permission: Required permission string (e.g., "inventory.view").

    Returns:
        Dependency function that raises HTTPException if user lacks permission.
    """
    async def permission_check(
        current_user: Annotated[User, Depends(get_current_user)],
        user_permissions: Annotated[set[str], Depends(get_user_permissions)],
    ) -> User:
        from app.core.auth.permissions import has_permission

        if not has_permission(user_permissions, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                        "message": "Insufficient permissions",
                        "details": {"required_permission": permission},
                    }
                },
            )
        return current_user

    return permission_check


def require_roles(*roles: str):
    """
    Dependency factory to require one or more global roles.

    Usage:
        @router.get("/admin/users")
        async def list_users(
            user: User = Depends(require_roles("admin", "owner")),
            db: Session = Depends(get_db)
        ):
            ...

    Args:
        *roles: One or more role names (e.g., "admin", "owner").

    Returns:
        Dependency function that raises HTTPException if user lacks all roles.
    """
    async def roles_check(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)],
    ) -> User:
        from app.services.permission_service import PermissionService

        permission_service = PermissionService(db)
        user_roles = permission_service.get_user_global_roles(current_user.id)

        if not any(role in user_roles for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "AUTH_INSUFFICIENT_ROLES",
                        "message": "Insufficient roles",
                        "details": {"required_roles": list(roles), "user_roles": user_roles},
                    }
                },
            )
        return current_user

    return roles_check


def require_any_permission(*permissions: str):
    """
    Dependency factory to require at least one of the specified permissions.

    Usage:
        @router.get("/items")
        async def list_items(
            user: User = Depends(require_any_permission("inventory.view", "inventory.edit")),
            db: Session = Depends(get_db)
        ):
            ...

    Args:
        *permissions: One or more permission strings.

    Returns:
        Dependency function that raises HTTPException if user lacks all permissions.
    """
    async def any_permission_check(
        current_user: Annotated[User, Depends(get_current_user)],
        user_permissions: Annotated[set[str], Depends(get_user_permissions)],
    ) -> User:
        from app.core.auth.permissions import has_permission

        if not any(has_permission(user_permissions, perm) for perm in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                        "message": "Insufficient permissions",
                        "details": {"required_permissions": list(permissions)},
                    }
                },
            )
        return current_user

    return any_permission_check
