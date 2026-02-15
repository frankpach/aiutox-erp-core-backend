"""Authentication and authorization core module."""

from fastapi import APIRouter

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
from app.core.module_interface import ModuleInterface, ModuleNavigationItem


class AuthCoreModule(ModuleInterface):
    """Core auth module metadata for dynamic navigation."""

    @property
    def module_id(self) -> str:
        return "auth"

    @property
    def module_type(self) -> str:
        return "core"

    @property
    def enabled(self) -> bool:
        return True

    def get_router(self) -> APIRouter | None:
        from app.api.v1.auth import router

        return router

    def get_settings_navigation(self) -> list[ModuleNavigationItem]:
        return [
            ModuleNavigationItem(
                id="auth.roles",
                label="Roles y permisos",
                path="/config/roles",
                permission="auth.manage_roles",
                icon="settings",
                category="Configuración",
                order=5,
            )
        ]


def create_module(_db: object | None = None) -> AuthCoreModule:
    return AuthCoreModule()

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
    "AuthCoreModule",
    "create_module",
]
