"""API dependencies - re-exports from core modules."""

from app.core.auth.dependencies import (
    get_current_user,
    get_user_permissions,
    require_any_permission,
    require_permission,
    require_roles,
    verify_tenant_access,
)
from app.core.db.deps import get_db

__all__ = [
    "get_current_user",
    "get_db",
    "get_user_permissions",
    "require_permission",
    "require_roles",
    "require_any_permission",
    "verify_tenant_access",
]
