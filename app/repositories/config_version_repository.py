"""Repository for configuration version management."""

from typing import Any
from uuid import UUID

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.config_version import ConfigVersion


class ConfigVersionRepository:
    """Repository for configuration version data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session.

        Args:
            db: Database session
        """
        self.db = db

    def create_version(
        self,
        config_id: UUID,
        tenant_id: UUID,
        module: str,
        key: str,
        value: Any,
        change_type: str,
        changed_by: UUID | None = None,
        change_reason: str | None = None,
        change_metadata: dict[str, Any] | None = None,
    ) -> ConfigVersion:
        """Create a new configuration version.

        Args:
            config_id: Configuration ID
            tenant_id: Tenant ID
            module: Module name
            key: Configuration key
            value: Configuration value
            change_type: Type of change ('create', 'update', 'delete')
            changed_by: User ID who made the change
            change_reason: Optional reason for the change
            change_metadata: Additional metadata

        Returns:
            Created ConfigVersion instance
        """
        # Get next version number for this config
        last_version = (
            self.db.query(func.max(ConfigVersion.version_number))
            .filter(
                ConfigVersion.tenant_id == tenant_id,
                ConfigVersion.module == module,
                ConfigVersion.key == key,
            )
            .scalar()
        )
        next_version = (last_version or 0) + 1

        # Create version
        version = ConfigVersion(
            config_id=config_id,
            tenant_id=tenant_id,
            module=module,
            key=key,
            value=value,
            version_number=next_version,
            change_type=change_type,
            changed_by=changed_by,
            change_reason=change_reason,
            change_metadata=change_metadata,
        )

        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def get_version(self, version_id: UUID) -> ConfigVersion | None:
        """Get a specific version by ID.

        Args:
            version_id: Version ID

        Returns:
            ConfigVersion instance or None
        """
        return (
            self.db.query(ConfigVersion).filter(ConfigVersion.id == version_id).first()
        )

    def get_version_by_number(
        self, tenant_id: UUID, module: str, key: str, version_number: int
    ) -> ConfigVersion | None:
        """Get a specific version by version number.

        Args:
            tenant_id: Tenant ID
            module: Module name
            key: Configuration key
            version_number: Version number

        Returns:
            ConfigVersion instance or None
        """
        return (
            self.db.query(ConfigVersion)
            .filter(
                ConfigVersion.tenant_id == tenant_id,
                ConfigVersion.module == module,
                ConfigVersion.key == key,
                ConfigVersion.version_number == version_number,
            )
            .first()
        )

    def get_latest_version(
        self, tenant_id: UUID, module: str, key: str
    ) -> ConfigVersion | None:
        """Get the latest version for a configuration.

        Args:
            tenant_id: Tenant ID
            module: Module name
            key: Configuration key

        Returns:
            Latest ConfigVersion instance or None
        """
        return (
            self.db.query(ConfigVersion)
            .filter(
                ConfigVersion.tenant_id == tenant_id,
                ConfigVersion.module == module,
                ConfigVersion.key == key,
            )
            .order_by(desc(ConfigVersion.version_number))
            .first()
        )

    def get_version_history(
        self,
        tenant_id: UUID,
        module: str,
        key: str,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ConfigVersion], int]:
        """Get version history for a configuration.

        Args:
            tenant_id: Tenant ID
            module: Module name
            key: Configuration key
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of versions, total count)
        """
        query = self.db.query(ConfigVersion).filter(
            ConfigVersion.tenant_id == tenant_id,
            ConfigVersion.module == module,
            ConfigVersion.key == key,
        )

        total = query.count()

        versions = (
            query.order_by(desc(ConfigVersion.version_number))
            .offset(skip)
            .limit(limit)
            .all()
        )

        return versions, total

    def get_module_history(
        self,
        tenant_id: UUID,
        module: str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[ConfigVersion], int]:
        """Get version history for all configurations in a module.

        Args:
            tenant_id: Tenant ID
            module: Module name
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of versions, total count)
        """
        query = self.db.query(ConfigVersion).filter(
            ConfigVersion.tenant_id == tenant_id,
            ConfigVersion.module == module,
        )

        total = query.count()

        versions = (
            query.order_by(desc(ConfigVersion.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

        return versions, total

    def delete_old_versions(
        self, tenant_id: UUID, module: str, key: str, keep_versions: int = 10
    ) -> int:
        """Delete old versions, keeping only the most recent ones.

        Args:
            tenant_id: Tenant ID
            module: Module name
            key: Configuration key
            keep_versions: Number of recent versions to keep

        Returns:
            Number of versions deleted
        """
        # Get versions to delete (all except the most recent keep_versions)
        versions_to_delete = (
            self.db.query(ConfigVersion.id)
            .filter(
                ConfigVersion.tenant_id == tenant_id,
                ConfigVersion.module == module,
                ConfigVersion.key == key,
            )
            .order_by(desc(ConfigVersion.version_number))
            .offset(keep_versions)
            .all()
        )

        if not versions_to_delete:
            return 0

        # Delete versions
        version_ids = [v.id for v in versions_to_delete]
        deleted = (
            self.db.query(ConfigVersion)
            .filter(ConfigVersion.id.in_(version_ids))
            .delete(synchronize_session=False)
        )

        self.db.commit()
        return deleted

    def get_version_count(self, tenant_id: UUID, module: str, key: str) -> int:
        """Get total number of versions for a configuration.

        Args:
            tenant_id: Tenant ID
            module: Module name
            key: Configuration key

        Returns:
            Total number of versions
        """
        return (
            self.db.query(ConfigVersion)
            .filter(
                ConfigVersion.tenant_id == tenant_id,
                ConfigVersion.module == module,
                ConfigVersion.key == key,
            )
            .count()
        )
