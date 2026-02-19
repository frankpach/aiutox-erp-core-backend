"""ThemePreset model for storing theme presets per tenant."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.core.db.session import Base


class ThemePreset(Base):
    """ThemePreset model for storing theme presets per tenant."""

    __tablename__ = "theme_presets"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenancy isolation",
    )
    name = Column(
        String(255),
        nullable=False,
        comment="Preset name (e.g., 'Original', 'Dark Mode')",
    )
    description = Column(
        Text,
        nullable=True,
        comment="Optional description of the preset",
    )
    config = Column(
        JSONB,
        nullable=False,
        comment="Theme configuration dictionary (colors, logos, fonts, etc.)",
    )
    is_default = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is the default preset for the tenant",
    )
    is_system = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is a system preset (cannot be deleted or edited)",
    )
    created_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who created this preset (NULL for system presets)",
    )
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        # Index for system presets lookup
        Index("idx_theme_presets_system", "is_system", "name"),
        # Index for tenant presets lookup
        Index("idx_theme_presets_tenant", "tenant_id", "is_default"),
        # Note: Partial unique index for "only one default per tenant" is created
        # in migration as: CREATE UNIQUE INDEX ... WHERE is_default = true
        # This cannot be expressed in SQLAlchemy table args, so it's in the migration
    )

    def __repr__(self) -> str:
        return (
            f"<ThemePreset(id={self.id}, tenant_id={self.tenant_id}, "
            f"name={self.name}, is_default={self.is_default}, is_system={self.is_system})>"
        )

