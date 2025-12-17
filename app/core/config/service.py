"""Config service for module configuration management."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config.schema import config_schema
from app.repositories.config_repository import ConfigRepository


class ConfigService:
    """Service for managing module configurations."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.repository = ConfigRepository(db)
        self.db = db

    def get(
        self, tenant_id: UUID, module: str, key: str, default: Any = None
    ) -> Any:
        """Get a configuration value.

        Args:
            tenant_id: Tenant ID
            module: Module name (e.g., 'products', 'inventory')
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        config = self.repository.get(tenant_id, module, key)
        if config:
            return config.value
        # Try to get default from schema
        schema_default = config_schema.get_default(module, key)
        return schema_default if schema_default is not None else default

    def set(
        self, tenant_id: UUID, module: str, key: str, value: Any
    ) -> dict[str, Any]:
        """Set a configuration value.

        Args:
            tenant_id: Tenant ID
            module: Module name
            key: Configuration key
            value: Value to set

        Returns:
            Dictionary with configuration data
        """
        # Validate schema if registered
        if not config_schema.validate(module, key, value):
            raise ValueError(
                f"Invalid value for {module}.{key}: value does not match schema"
            )

        # Update if exists, create if not
        if self.repository.exists(tenant_id, module, key):
            config = self.repository.update(tenant_id, module, key, value)
        else:
            config = self.repository.create(tenant_id, module, key, value)

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
        self, tenant_id: UUID, module: str, config_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """Set multiple configuration values for a module.

        Args:
            tenant_id: Tenant ID
            module: Module name
            config_dict: Dictionary of key-value pairs to set

        Returns:
            Dictionary of all configuration for the module
        """
        for key, value in config_dict.items():
            self.set(tenant_id, module, key, value)
        return self.get_module_config(tenant_id, module)

    def delete(self, tenant_id: UUID, module: str, key: str) -> None:
        """Delete a configuration entry.

        Args:
            tenant_id: Tenant ID
            module: Module name
            key: Configuration key
        """
        self.repository.delete(tenant_id, module, key)

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










