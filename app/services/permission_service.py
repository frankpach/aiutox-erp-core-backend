"""Permission service for calculating user permissions based on roles."""

from datetime import datetime
from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session

from app.core.auth.permissions import (
    MODULE_ROLES,
    ROLE_PERMISSIONS,
    has_permission,
)
from app.core.exceptions import (
    APIException,
    raise_bad_request,
    raise_forbidden,
    raise_internal_server_error,
    raise_not_found,
)
from app.core.logging import create_audit_log_entry, log_permission_change
from app.models.delegated_permission import DelegatedPermission
from app.models.module_role import ModuleRole
from app.models.user_role import UserRole
from app.repositories.permission_repository import PermissionRepository


class PermissionService:
    """Service for calculating and managing user permissions."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db

    def get_user_global_roles(self, user_id: UUID) -> list[str]:
        """
        Get global roles for a user.

        Args:
            user_id: User UUID.

        Returns:
            List of role strings (e.g., ["admin", "manager"]).
        """
        roles = (
            self.db.query(UserRole)
            .filter(UserRole.user_id == user_id)
            .all()
        )
        return [role.role for role in roles]

    def get_role_permissions(self, role: str) -> set[str]:
        """
        Get permissions for a specific role.

        Args:
            role: Role name (e.g., "admin", "viewer").

        Returns:
            Set of permission strings for the role.
            Returns empty set if role is not found.
        """
        return ROLE_PERMISSIONS.get(role, set())

    def get_user_module_roles(self, user_id: UUID) -> list[ModuleRole]:
        """
        Get module roles for a user.

        Args:
            user_id: User UUID.

        Returns:
            List of ModuleRole objects.
        """
        return (
            self.db.query(ModuleRole)
            .filter(ModuleRole.user_id == user_id)
            .all()
        )

    def get_module_role_permissions(self, module: str, role_name: str) -> set[str]:
        """
        Get permissions for a specific module role.

        Args:
            module: Module name (e.g., "inventory", "products").
            role_name: Role name (e.g., "editor", "viewer", "manager").
                      Can include "internal." prefix or not.

        Returns:
            Set of permission strings for the module role.
            Returns empty set if module or role is not found.
        """
        # Normalizar role_name: remover prefijo "internal." si existe
        normalized_role = role_name
        if normalized_role.startswith("internal."):
            normalized_role = normalized_role[9:]  # Remover "internal."

        # Construir clave completa
        full_role_name = f"internal.{normalized_role}"

        module_roles = MODULE_ROLES.get(module, {})
        return module_roles.get(full_role_name, set())

    def get_effective_permissions(self, user_id: UUID) -> set[str]:
        """
        Get effective permissions for a user.

        Phase 4: Includes global roles, module roles, and delegated permissions.

        The effective permissions are the union of all permissions from:
        1. Global roles (Phase 2)
        2. Module roles (Phase 3)
        3. Delegated permissions (Phase 4)

        Args:
            user_id: User UUID.

        Returns:
            Set of permission strings (union of all permission sources).
        """
        permissions = set()

        # 1. Permisos de roles globales
        global_roles = self.get_user_global_roles(user_id)
        for role in global_roles:
            role_permissions = self.get_role_permissions(role)
            permissions.update(role_permissions)

        # 2. Permisos de roles internos de módulo
        module_roles = self.get_user_module_roles(user_id)
        for module_role in module_roles:
            role_permissions = self.get_module_role_permissions(
                module_role.module, module_role.role_name
            )
            permissions.update(role_permissions)

        # 3. Permisos delegados activos (Phase 4)
        delegated_permissions = self.get_user_delegated_permissions(user_id)
        for perm in delegated_permissions:
            permissions.add(perm.permission)

        return permissions

    def get_user_delegated_permissions(self, user_id: UUID) -> list[DelegatedPermission]:
        """
        Get all active delegated permissions for a user.

        Args:
            user_id: User UUID.

        Returns:
            List of active DelegatedPermission instances.
        """
        repo = PermissionRepository(self.db)
        return repo.get_active_delegated_permissions(user_id)

    def grant_permission(
        self,
        user_id: UUID,
        module: str,
        permission: str,
        expires_at: datetime | None,
        granted_by: UUID,
    ) -> DelegatedPermission:
        """
        Grant a delegated permission to a user.

        Validaciones:
        1. granted_by debe tener {module}.manage_users
        2. permission NO puede ser *.manage_users
        3. permission NO puede ser global (auth.*, system.*)
        4. permission debe pertenecer al módulo (module.action)

        Args:
            user_id: ID of the user receiving the permission.
            module: Module name (e.g., "inventory", "products").
            permission: Permission string (e.g., "inventory.edit").
            expires_at: Expiration datetime. If None, permission does not expire.
            granted_by: ID of the user granting the permission.

        Returns:
            Created DelegatedPermission instance.

        Raises:
            APIException: If validations fail.
        """
        # Validación 1: Verificar que granted_by tiene {module}.manage_users
        granted_by_permissions = self.get_effective_permissions(granted_by)
        required_permission = f"{module}.manage_users"
        if not has_permission(granted_by_permissions, required_permission):
            raise_forbidden(
                code="PERMISSION_DENIED",
                message=f"User does not have permission '{required_permission}' to grant permissions",
            )

        # Validación 2: permission NO puede ser *.manage_users
        if permission.endswith(".manage_users"):
            raise_bad_request(
                code="INVALID_PERMISSION",
                message="Cannot delegate permission '*.manage_users'. Only system administrators can grant this permission.",
            )

        # Validación 3: permission NO puede ser global (auth.*, system.*)
        if permission.startswith("auth.") or permission.startswith("system."):
            raise_bad_request(
                code="INVALID_PERMISSION",
                message="Cannot delegate global permissions (auth.*, system.*). Only system administrators can grant these permissions.",
            )

        # Validación 4: permission debe pertenecer al módulo (module.action)
        if not permission.startswith(f"{module}."):
            raise_bad_request(
                code="INVALID_PERMISSION",
                message=f"Permission '{permission}' does not belong to module '{module}'. Permission must start with '{module}.'",
            )

        # Crear el permiso delegado
        repo = PermissionRepository(self.db)
        try:
            delegated_permission = repo.create_delegated_permission(
                user_id=user_id,
                granted_by=granted_by,
                module=module,
                permission=permission,
                expires_at=expires_at,
            )

            # Log to console
            log_permission_change(
                user_id=str(granted_by),
                action="grant_delegated_permission",
                target_user_id=str(user_id),
                details={
                    "module": module,
                    "permission": permission,
                    "expires_at": str(expires_at) if expires_at else None,
                    "permission_id": str(delegated_permission.id),
                },
            )

            # Get tenant_id from the user who granted the permission
            from app.repositories.user_repository import UserRepository

            user_repo = UserRepository(self.db)
            granter_user = user_repo.get_by_id(granted_by)
            if granter_user:
                # Create audit log entry
                create_audit_log_entry(
                    db=self.db,
                    user_id=granted_by,
                    tenant_id=granter_user.tenant_id,
                    action="grant_delegated_permission",
                    resource_type="permission",
                    resource_id=delegated_permission.id,
                    details={
                        "module": module,
                        "permission": permission,
                        "expires_at": str(expires_at) if expires_at else None,
                        "target_user_id": str(user_id),
                    },
                )

            return delegated_permission
        except Exception as e:
            # Manejar constraint único (mismo líder, mismo permiso, mismo usuario)
            if "uq_delegated_permissions" in str(e).lower():
                raise APIException(
                    code="PERMISSION_ALREADY_EXISTS",
                    message=f"Permission '{permission}' already granted to this user by you. Revoke it first to grant it again.",
                    status_code=status.HTTP_409_CONFLICT,
                ) from e
            raise

    def revoke_permission(
        self,
        permission_id: UUID,
        revoked_by: UUID,
    ) -> None:
        """
        Revoke a delegated permission.

        Validaciones:
        1. revoked_by debe ser quien otorgó el permiso O tener auth.manage_users

        Args:
            permission_id: Permission UUID to revoke.
            revoked_by: UUID of the user revoking the permission.

        Raises:
            APIException: If permission not found or user doesn't have permission to revoke.
        """
        repo = PermissionRepository(self.db)
        permission = repo.get_delegated_permission_by_id(permission_id)

        if not permission:
            raise_not_found("Permission", str(permission_id))

        # Verificar si ya está revocado
        if permission.revoked_at is not None:
            raise_bad_request(
                code="PERMISSION_ALREADY_REVOKED",
                message="Permission is already revoked",
            )

        # Validación: revoked_by debe ser quien otorgó el permiso O tener auth.manage_users
        revoked_by_permissions = self.get_effective_permissions(revoked_by)
        can_revoke = (
            permission.granted_by == revoked_by
            or has_permission(revoked_by_permissions, "auth.manage_users")
        )

        if not can_revoke:
            raise_forbidden(
                code="PERMISSION_DENIED",
                message="You can only revoke permissions you granted, or you need 'auth.manage_users' permission",
            )

        # Revocar el permiso
        success = repo.revoke_permission(permission_id, revoked_by)
        if not success:
            raise_internal_server_error(
                code="REVOKE_FAILED",
                message="Failed to revoke permission",
            )

        # Log to console
        log_permission_change(
            user_id=str(revoked_by),
            action="revoke_delegated_permission",
            target_user_id=str(permission.user_id),
            details={
                "module": permission.module,
                "permission": permission.permission,
                "permission_id": str(permission.id),
                "original_granted_by": str(permission.granted_by),
            },
        )

        # Get tenant_id from the user who revoked the permission
        from app.repositories.user_repository import UserRepository

        user_repo = UserRepository(self.db)
        revoker_user = user_repo.get_by_id(revoked_by)
        if revoker_user:
            # Create audit log entry
            create_audit_log_entry(
                db=self.db,
                user_id=revoked_by,
                tenant_id=revoker_user.tenant_id,
                action="revoke_delegated_permission",
                resource_type="permission",
                resource_id=permission.id,
                details={
                    "module": permission.module,
                    "permission": permission.permission,
                    "target_user_id": str(permission.user_id),
                    "original_granted_by": str(permission.granted_by),
                },
            )

    def revoke_all_user_permissions(
        self,
        user_id: UUID,
        revoked_by: UUID,
    ) -> int:
        """
        Revoke ALL delegated permissions of a user.

        Validaciones:
        1. revoked_by debe tener auth.manage_users o rol owner/admin

        Args:
            user_id: User UUID whose permissions will be revoked.
            revoked_by: UUID of the user revoking the permissions.

        Returns:
            Number of permissions revoked.

        Raises:
            APIException: If user doesn't have permission to revoke.
        """
        # Validación: revoked_by debe tener auth.manage_users o rol owner/admin
        revoked_by_permissions = self.get_effective_permissions(revoked_by)
        revoked_by_roles = self.get_user_global_roles(revoked_by)

        can_revoke = (
            has_permission(revoked_by_permissions, "auth.manage_users")
            or "owner" in revoked_by_roles
            or "admin" in revoked_by_roles
        )

        if not can_revoke:
            raise_forbidden(
                code="PERMISSION_DENIED",
                message="Only administrators or owners can revoke all permissions of a user",
            )

        # Revocar todos los permisos
        repo = PermissionRepository(self.db)
        revoked_count = repo.revoke_all_user_permissions(user_id, revoked_by)

        # Log to console
        log_permission_change(
            user_id=str(revoked_by),
            action="revoke_all_delegated_permissions",
            target_user_id=str(user_id),
            details={"revoked_count": revoked_count},
        )

        # Get tenant_id from the user who revoked the permissions
        from app.repositories.user_repository import UserRepository

        user_repo = UserRepository(self.db)
        revoker_user = user_repo.get_by_id(revoked_by)
        if revoker_user:
            # Create audit log entry
            create_audit_log_entry(
                db=self.db,
                user_id=revoked_by,
                tenant_id=revoker_user.tenant_id,
                action="revoke_all_delegated_permissions",
                resource_type="user",
                resource_id=user_id,
                details={"revoked_count": revoked_count},
            )

        return revoked_count

