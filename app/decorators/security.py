"""
Security decorators for AiutoX ERP
Provides RBAC and permission validation decorators
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import status

from app.core.auth.permissions import check_permission
from app.core.exceptions import APIException


def require_permission(permission: str) -> Callable:
    """
    Decorator to require specific permission for endpoint access.

    Args:
        permission: Permission string required (e.g., "tasks.manage")

    Returns:
        Decorated function with permission check
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Extract current_user from kwargs (FastAPI dependency injection)
            current_user = kwargs.get("current_user")
            if not current_user:
                raise APIException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    code="AUTHENTICATION_REQUIRED",
                    message="Authentication required",
                )

            # Check permission
            if not check_permission(current_user, permission):
                raise APIException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    code="INSUFFICIENT_PERMISSIONS",
                    message=f"Permission '{permission}' required",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_ownership(resource_id_param: str = "task_id") -> Callable:
    """
    Decorator to require resource ownership or admin access.

    Args:
        resource_id_param: Parameter name containing resource ID

    Returns:
        Decorated function with ownership check
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            current_user = kwargs.get("current_user")
            if not current_user:
                raise APIException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    code="AUTHENTICATION_REQUIRED",
                    message="Authentication required",
                )

            # Get resource ID from function parameters
            resource_id = kwargs.get(resource_id_param)
            if not resource_id:
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    code="INVALID_RESOURCE_ID",
                    message=f"Resource ID '{resource_id_param}' required",
                )

            # Check ownership or admin
            from app.core.auth.permissions import is_owner_or_admin

            if not is_owner_or_admin(current_user, resource_id):
                raise APIException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    code="ACCESS_DENIED",
                    message="Access denied: resource ownership required",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def validate_tenant_access() -> Callable:
    """
    Decorator to validate tenant access for multi-tenant isolation.

    Returns:
        Decorated function with tenant validation
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            current_user = kwargs.get("current_user")
            if not current_user or not current_user.tenant_id:
                raise APIException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    code="INVALID_TENANT",
                    message="Valid tenant required",
                )

            # Additional tenant validation logic can be added here
            # For now, we rely on the tenant filtering in repositories

            return await func(*args, **kwargs)

        return wrapper

    return decorator
