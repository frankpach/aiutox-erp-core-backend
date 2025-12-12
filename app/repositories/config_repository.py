"""Config repository for data access operations."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.system_config import SystemConfig


class ConfigRepository:
    """Repository for system configuration data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def get(
        self, tenant_id: UUID, module: str, key: str
    ) -> SystemConfig | None:
        """Get configuration by tenant, module, and key."""
        return (
            self.db.query(SystemConfig)
            .filter(
                SystemConfig.tenant_id == tenant_id,
                SystemConfig.module == module,
                SystemConfig.key == key,
            )
            .first()
        )

    def get_all_by_module(
        self, tenant_id: UUID, module: str
    ) -> list[SystemConfig]:
        """Get all configurations for a module in a tenant."""
        return (
            self.db.query(SystemConfig)
            .filter(
                SystemConfig.tenant_id == tenant_id,
                SystemConfig.module == module,
            )
            .all()
        )

    def create(
        self, tenant_id: UUID, module: str, key: str, value: Any
    ) -> SystemConfig:
        """Create a new configuration entry."""
        config = SystemConfig(
            tenant_id=tenant_id,
            module=module,
            key=key,
            value=value,
        )
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def update(
        self, tenant_id: UUID, module: str, key: str, value: Any
    ) -> SystemConfig:
        """Update an existing configuration entry."""
        config = self.get(tenant_id, module, key)
        if not config:
            raise ValueError(
                f"Configuration not found: tenant_id={tenant_id}, module={module}, key={key}"
            )
        config.value = value
        self.db.commit()
        self.db.refresh(config)
        return config

    def delete(self, tenant_id: UUID, module: str, key: str) -> None:
        """Delete a configuration entry."""
        config = self.get(tenant_id, module, key)
        if config:
            self.db.delete(config)
            self.db.commit()

    def exists(self, tenant_id: UUID, module: str, key: str) -> bool:
        """Check if a configuration entry exists."""
        return (
            self.db.query(SystemConfig)
            .filter(
                SystemConfig.tenant_id == tenant_id,
                SystemConfig.module == module,
                SystemConfig.key == key,
            )
            .first()
            is not None
        )



