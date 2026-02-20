"""Config service for module configuration management."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config.cache import get_config_cache
from app.core.config.schema import config_schema
from app.core.logging import create_audit_log_entry
from app.repositories.config_repository import ConfigRepository
from app.repositories.config_version_repository import ConfigVersionRepository


class ConfigService:
    """Service for managing module configurations with audit logging, caching, and versioning."""

    def __init__(
        self, db: Session, use_cache: bool = True, use_versioning: bool = True
    ):
        """Initialize service with database session.

        Args:
            db: Database session
            use_cache: Whether to use Redis cache (default: True)
            use_versioning: Whether to track configuration versions (default: True)
        """
        self.repository = ConfigRepository(db)
        self.version_repository = (
            ConfigVersionRepository(db) if use_versioning else None
        )
        self.db = db
        self.cache = get_config_cache(enabled=use_cache) if use_cache else None
        self.use_versioning = use_versioning

    def get(self, tenant_id: UUID, module: str, key: str, default: Any = None) -> Any:
        """Get a configuration value with caching.

        Args:
            tenant_id: Tenant ID
            module: Module name (e.g., 'products', 'inventory')
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        # Try cache first
        if self.cache:
            cached_value = self.cache.get(tenant_id, module, key)
            if cached_value is not None:
                return cached_value

        # Get from database
        config = self.repository.get(tenant_id, module, key)
        if config:
            value = config.value
            # Cache the value
            if self.cache:
                self.cache.set(tenant_id, module, key, value)
            return value

        # Try to get default from schema
        schema_default = config_schema.get_default(module, key)
        result = schema_default if schema_default is not None else default

        # Cache default values too (with shorter TTL)
        if result is not None and self.cache:
            self.cache.set(tenant_id, module, key, result, ttl=60)

        return result

    def set(
        self,
        tenant_id: UUID,
        module: str,
        key: str,
        value: Any,
        user_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Set a configuration value with audit logging.

        Args:
            tenant_id: Tenant ID
            module: Module name
            key: Configuration key
            value: Value to set
            user_id: User ID who made the change (for audit)
            ip_address: Client IP address (for audit)
            user_agent: Client user agent (for audit)

        Returns:
            Dictionary with configuration data
        """
        # Validate schema if registered
        if not config_schema.validate(module, key, value):
            raise ValueError(
                f"Invalid value for {module}.{key}: value does not match schema"
            )

        # Check if update or create
        is_update = self.repository.exists(tenant_id, module, key)
        old_value = None
        if is_update:
            old_config = self.repository.get(tenant_id, module, key)
            old_value = old_config.value if old_config else None
            config = self.repository.update(tenant_id, module, key, value)
        else:
            config = self.repository.create(tenant_id, module, key, value)

        # Create version record
        if self.use_versioning and self.version_repository:
            change_type = "update" if is_update else "create"
            version_metadata = {}
            if ip_address:
                version_metadata["ip_address"] = ip_address
            if user_agent:
                version_metadata["user_agent"] = user_agent

            self.version_repository.create_version(
                config_id=config.id,
                tenant_id=tenant_id,
                module=module,
                key=key,
                value=value,
                change_type=change_type,
                changed_by=user_id,
                change_metadata=version_metadata if version_metadata else None,
            )

        # Invalidate cache for this key
        if self.cache:
            self.cache.delete(tenant_id, module, key)

        # Audit log
        action = "config.updated" if is_update else "config.created"
        details = {
            "module": module,
            "key": key,
            "old_value": old_value,
            "new_value": value,
        }
        create_audit_log_entry(
            db=self.db,
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            resource_type="config",
            resource_id=config.id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Cache the new value
        if self.cache:
            self.cache.set(tenant_id, module, key, value)

        return {
            "id": config.id,
            "tenant_id": config.tenant_id,
            "module": config.module,
            "key": config.key,
            "value": config.value,
        }

    def get_module_config(self, tenant_id: UUID, module: str) -> dict[str, Any]:
        """Get all configuration for a module.

        Args:
            tenant_id: Tenant ID
            module: Module name

        Returns:
            Dictionary of all configuration keys and values
        """
        configs = self.repository.get_all_by_module(tenant_id, module)
        result = {}
        for config in configs:
            result[config.key] = config.value
        return result

    def set_module_config(
        self,
        tenant_id: UUID,
        module: str,
        config_dict: dict[str, Any],
        user_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Set multiple configuration values for a module with audit logging.

        Args:
            tenant_id: Tenant ID
            module: Module name
            config_dict: Dictionary of key-value pairs to set
            user_id: User ID who made the change (for audit)
            ip_address: Client IP address (for audit)
            user_agent: Client user agent (for audit)

        Returns:
            Dictionary of all configuration for the module
        """
        for key, value in config_dict.items():
            self.set(
                tenant_id,
                module,
                key,
                value,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        return self.get_module_config(tenant_id, module)

    def delete(
        self,
        tenant_id: UUID,
        module: str,
        key: str,
        user_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Delete a configuration entry with audit logging.

        Args:
            tenant_id: Tenant ID
            module: Module name
            key: Configuration key
            user_id: User ID who made the change (for audit)
            ip_address: Client IP address (for audit)
            user_agent: Client user agent (for audit)
        """
        # Get old value for audit
        old_config = self.repository.get(tenant_id, module, key)
        old_value = old_config.value if old_config else None
        config_id = old_config.id if old_config else None

        # Create version record before deletion
        if self.use_versioning and self.version_repository and old_config:
            version_metadata = {}
            if ip_address:
                version_metadata["ip_address"] = ip_address
            if user_agent:
                version_metadata["user_agent"] = user_agent

            self.version_repository.create_version(
                config_id=old_config.id,
                tenant_id=tenant_id,
                module=module,
                key=key,
                value=old_value,
                change_type="delete",
                changed_by=user_id,
                change_metadata=version_metadata if version_metadata else None,
            )

        # Delete
        self.repository.delete(tenant_id, module, key)

        # Invalidate cache
        if self.cache:
            self.cache.delete(tenant_id, module, key)

        # Audit log
        details = {
            "module": module,
            "key": key,
            "old_value": old_value,
        }
        create_audit_log_entry(
            db=self.db,
            user_id=user_id,
            tenant_id=tenant_id,
            action="config.deleted",
            resource_type="config",
            resource_id=config_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def validate_schema(self, module: str, key: str, value: Any) -> bool:
        """Validate a value against its schema.

        Args:
            module: Module name
            key: Configuration key
            value: Value to validate

        Returns:
            True if valid, False otherwise
        """
        return config_schema.validate(module, key, value)

    def clear_cache(
        self, tenant_id: UUID | None = None, module: str | None = None
    ) -> int:
        """Clear configuration cache.

        Args:
            tenant_id: Tenant ID (if None, clears all tenants)
            module: Module name (if None, clears all modules)

        Returns:
            Number of entries cleared
        """
        if not self.cache:
            return 0

        if module and tenant_id:
            # Clear specific module
            return self.cache.invalidate_module(tenant_id, module)
        elif not tenant_id and not module:
            # Clear all cache
            self.cache.clear_all()
            return -1  # Unknown count
        else:
            # Not supported combination
            return 0

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        if not self.cache:
            return {"enabled": False, "status": "disabled"}

        return self.cache.get_stats()

    def get_version_history(
        self, tenant_id: UUID, module: str, key: str, skip: int = 0, limit: int = 50
    ) -> tuple[list[dict[str, Any]], int]:
        """Get version history for a configuration.

        Args:
            tenant_id: Tenant ID
            module: Module name
            key: Configuration key
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of version dicts, total count)
        """
        if not self.use_versioning or not self.version_repository:
            return [], 0

        versions, total = self.version_repository.get_version_history(
            tenant_id, module, key, skip, limit
        )

        version_list = []
        for version in versions:
            version_list.append(
                {
                    "id": version.id,
                    "version_number": version.version_number,
                    "value": version.value,
                    "change_type": version.change_type,
                    "changed_by": version.changed_by,
                    "change_reason": version.change_reason,
                    "created_at": version.created_at,
                    "metadata": version.metadata,
                }
            )

        return version_list, total

    def rollback_to_version(
        self,
        tenant_id: UUID,
        module: str,
        key: str,
        version_number: int,
        user_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Rollback a configuration to a specific version.

        Args:
            tenant_id: Tenant ID
            module: Module name
            key: Configuration key
            version_number: Version number to rollback to
            user_id: User ID performing the rollback
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Dictionary with updated configuration data

        Raises:
            ValueError: If version not found or versioning disabled
        """
        if not self.use_versioning or not self.version_repository:
            raise ValueError("Versioning is not enabled")

        # Get the target version
        target_version = self.version_repository.get_version_by_number(
            tenant_id, module, key, version_number
        )

        if not target_version:
            raise ValueError(f"Version {version_number} not found for {module}.{key}")

        # Set the value from the target version
        return self.set(
            tenant_id=tenant_id,
            module=module,
            key=key,
            value=target_version.value,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def cleanup_old_versions(
        self, tenant_id: UUID, module: str, key: str, keep_versions: int = 10
    ) -> int:
        """Clean up old versions, keeping only recent ones.

        Args:
            tenant_id: Tenant ID
            module: Module name
            key: Configuration key
            keep_versions: Number of recent versions to keep

        Returns:
            Number of versions deleted
        """
        if not self.use_versioning or not self.version_repository:
            return 0

        return self.version_repository.delete_old_versions(
            tenant_id, module, key, keep_versions
        )
