"""Permission repository for delegated permission data access operations."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.delegated_permission import DelegatedPermission


class PermissionRepository:
    """Repository for delegated permission data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create_delegated_permission(
        self,
        user_id: UUID,
        granted_by: UUID,
        module: str,
        permission: str,
        expires_at: datetime | None = None,
    ) -> DelegatedPermission:
        """
        Create a new delegated permission.

        Args:
            user_id: ID of the user receiving the permission.
            granted_by: ID of the user granting the permission.
            module: Module name (e.g., "inventory", "products").
            permission: Permission string (e.g., "inventory.edit").
            expires_at: Expiration datetime. If None, permission does not expire.

        Returns:
            Created DelegatedPermission instance.

        Raises:
            IntegrityError: If unique constraint is violated.
        """
        delegated_permission = DelegatedPermission(
            user_id=user_id,
            granted_by=granted_by,
            module=module,
            permission=permission,
            expires_at=expires_at,
        )
        self.db.add(delegated_permission)
        self.db.commit()
        self.db.refresh(delegated_permission)
        return delegated_permission

    def get_active_delegated_permissions(
        self,
        user_id: UUID,
    ) -> list[DelegatedPermission]:
        """
        Get all active delegated permissions for a user.

        Active = revoked_at IS NULL AND (expires_at IS NULL OR expires_at > now()).

        Args:
            user_id: User UUID.

        Returns:
            List of active DelegatedPermission instances.
        """
        now = datetime.now(timezone.utc)
        return (
            self.db.query(DelegatedPermission)
            .filter(
                DelegatedPermission.user_id == user_id,
                DelegatedPermission.revoked_at.is_(None),
                or_(
                    DelegatedPermission.expires_at.is_(None),
                    DelegatedPermission.expires_at > now,
                ),
            )
            .all()
        )

    def get_delegated_permission_by_id(
        self,
        permission_id: UUID,
    ) -> DelegatedPermission | None:
        """
        Get a delegated permission by ID.

        Args:
            permission_id: Permission UUID.

        Returns:
            DelegatedPermission instance or None if not found.
        """
        return (
            self.db.query(DelegatedPermission)
            .filter(DelegatedPermission.id == permission_id)
            .first()
        )

    def revoke_permission(
        self,
        permission_id: UUID,
        revoked_by: UUID,
    ) -> bool:
        """
        Revoke a delegated permission by setting revoked_at.

        Args:
            permission_id: Permission UUID to revoke.
            revoked_by: UUID of the user revoking the permission.

        Returns:
            True if permission was revoked, False if not found or already revoked.
        """
        permission = self.get_delegated_permission_by_id(permission_id)
        if not permission or permission.revoked_at is not None:
            return False

        permission.revoked_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(permission)
        return True

    def revoke_all_user_permissions(
        self,
        user_id: UUID,
        revoked_by: UUID,
    ) -> int:
        """
        Revoke ALL active delegated permissions for a user.

        Args:
            user_id: User UUID whose permissions will be revoked.
            revoked_by: UUID of the user revoking the permissions.

        Returns:
            Number of permissions revoked.
        """
        now = datetime.now(timezone.utc)
        permissions = (
            self.db.query(DelegatedPermission)
            .filter(
                DelegatedPermission.user_id == user_id,
                DelegatedPermission.revoked_at.is_(None),
            )
            .all()
        )

        count = 0
        for permission in permissions:
            permission.revoked_at = now
            count += 1

        if count > 0:
            self.db.commit()

        return count

    def get_permissions_by_granted_by(
        self,
        granted_by: UUID,
    ) -> list[DelegatedPermission]:
        """
        Get all permissions granted by a specific user.

        Args:
            granted_by: UUID of the user who granted the permissions.

        Returns:
            List of DelegatedPermission instances.
        """
        return (
            self.db.query(DelegatedPermission)
            .filter(DelegatedPermission.granted_by == granted_by)
            .all()
        )

    def get_user_module_permissions(
        self,
        user_id: UUID,
        module: str,
    ) -> list[DelegatedPermission]:
        """
        Get all delegated permissions for a user in a specific module.

        Args:
            user_id: User UUID.
            module: Module name.

        Returns:
            List of DelegatedPermission instances (including revoked and expired).
        """
        return (
            self.db.query(DelegatedPermission)
            .filter(
                DelegatedPermission.user_id == user_id,
                DelegatedPermission.module == module,
            )
            .all()
        )

