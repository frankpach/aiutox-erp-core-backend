"""Pydantic schemas for API requests and responses."""

from app.schemas.audit import AuditLogListResponse, AuditLogResponse
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshTokenRequest,
    RoleAssignRequest,
    RoleListResponse,
    RoleResponse,
    TokenResponse,
    UserMeResponse,
)
from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    PaginationMeta,
    StandardListResponse,
    StandardResponse,
)
from app.schemas.contact import (
    ContactBase,
    ContactCreate,
    ContactResponse,
    ContactUpdate,
)
from app.schemas.contact_method import (
    ContactMethodBase,
    ContactMethodCreate,
    ContactMethodResponse,
    ContactMethodUpdate,
)
from app.schemas.organization import (
    OrganizationBase,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.schemas.permission import (
    DelegatedPermissionCreate,
    DelegatedPermissionListResponse,
    DelegatedPermissionResponse,
    PermissionGrantRequest,
    RevokePermissionResponse,
)
from app.schemas.tenant import (
    TenantBase,
    TenantCreate,
    TenantResponse,
    TenantUpdate,
)
from app.schemas.user import UserBase, UserCreate, UserResponse, UserUpdate

__all__ = [
    "ErrorDetail",
    "ErrorResponse",
    "PaginationMeta",
    "StandardListResponse",
    "StandardResponse",
    "AuditLogListResponse",
    "AuditLogResponse",
    "AccessTokenResponse",
    "LoginRequest",
    "RefreshTokenRequest",
    "RoleAssignRequest",
    "RoleListResponse",
    "RoleResponse",
    "TokenResponse",
    "UserMeResponse",
    "ContactBase",
    "ContactCreate",
    "ContactResponse",
    "ContactUpdate",
    "ContactMethodBase",
    "ContactMethodCreate",
    "ContactMethodResponse",
    "ContactMethodUpdate",
    "OrganizationBase",
    "OrganizationCreate",
    "OrganizationResponse",
    "OrganizationUpdate",
    "TenantBase",
    "TenantCreate",
    "TenantResponse",
    "TenantUpdate",
    "UserBase",
    "UserCreate",
    "UserResponse",
    "UserUpdate",
    "DelegatedPermissionCreate",
    "DelegatedPermissionResponse",
    "DelegatedPermissionListResponse",
    "PermissionGrantRequest",
    "RevokePermissionResponse",
]
