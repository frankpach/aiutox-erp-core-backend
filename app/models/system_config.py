"""SystemConfig model for module configuration management."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID

from app.core.db.session import Base


class SystemConfig(Base):
    """SystemConfig model for storing module-specific configuration per tenant."""

    __tablename__ = "system_configs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenancy isolation",
    )
    module = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Module name (e.g., 'products', 'inventory')",
    )
    key = Column(
        String(255),
        nullable=False,
        comment="Configuration key",
    )
    value = Column(
        JSONB,
        nullable=False,
        comment="Configuration value (JSON)",
    )
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "module", "key", name="uq_system_configs_tenant_module_key"
        ),
        Index("idx_system_configs_tenant_module", "tenant_id", "module"),
    )

    def __repr__(self) -> str:
        return (
            f"<SystemConfig(id={self.id}, tenant_id={self.tenant_id}, "
            f"module={self.module}, key={self.key})>"
        )




