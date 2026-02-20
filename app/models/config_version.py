"""ConfigVersion model for configuration versioning and history."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class ConfigVersion(Base):
    """ConfigVersion model for tracking configuration changes over time.

    This model stores historical versions of configuration values,
    allowing rollback and audit trail of configuration changes.
    """

    __tablename__ = "config_versions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    config_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("system_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the configuration entry",
    )
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenancy isolation",
    )
    module = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Module name (e.g., 'products', 'inventory', 'app_theme')",
    )
    key = Column(
        String(200),
        nullable=False,
        index=True,
        comment="Configuration key within the module",
    )
    value = Column(
        JSONB,
        nullable=False,
        comment="Configuration value (stored as JSON for flexibility)",
    )
    version_number = Column(
        Integer,
        nullable=False,
        comment="Sequential version number for this config key",
    )
    change_type = Column(
        String(20),
        nullable=False,
        comment="Type of change: 'create', 'update', 'delete'",
    )
    changed_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who made the change (null for system changes)",
    )
    change_reason = Column(
        Text,
        nullable=True,
        comment="Optional reason for the change",
    )
    change_metadata = Column(
        JSONB,
        nullable=True,
        comment="Additional metadata (IP, user agent, etc.)",
    )
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
        comment="Timestamp when this version was created",
    )

    # Relationships
    config = relationship("SystemConfig", foreign_keys=[config_id])
    user = relationship("User", foreign_keys=[changed_by])

    __table_args__ = (
        # Composite index for efficient queries
        Index("ix_config_versions_tenant_module", tenant_id, module),
        Index("ix_config_versions_config_version", config_id, version_number),
        Index("ix_config_versions_tenant_module_key", tenant_id, module, key),
    )

    def __repr__(self) -> str:
        """String representation of ConfigVersion."""
        return (
            f"<ConfigVersion(id={self.id}, module={self.module}, "
            f"key={self.key}, version={self.version_number})>"
        )
