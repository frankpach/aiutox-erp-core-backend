"""Authentication and authorization core module."""

from app.core.auth.dependencies import (
    get_current_user,
    get_user_permissions,
    require_any_permission,
    require_permission,
    require_roles,
    verify_tenant_access,
)
from app.core.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_refresh_token,
)
from app.core.auth.password import hash_password, verify_password
from app.core.auth.rate_limit import (
    check_login_rate_limit,
    create_rate_limit_exception,
    limiter,
    record_login_attempt,
)
from app.core.auth.token_hash import hash_token, verify_token

__all__ = [
    "get_current_user",
    "get_user_permissions",
    "require_any_permission",
    "require_permission",
    "require_roles",
    "verify_tenant_access",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "verify_refresh_token",
    "hash_password",
    "verify_password",
    "check_login_rate_limit",
    "create_rate_limit_exception",
    "limiter",
    "record_login_attempt",
    "hash_token",
    "verify_token",
]
