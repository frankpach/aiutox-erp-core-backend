"""View models for saved filters and custom views management."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID

from app.core.db.session import Base


class SavedFilter(Base):
    """Saved filter model for reusable filter configurations."""

    __tablename__ = "saved_filters"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Filter information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    module = Column(String(50), nullable=False, index=True)  # e.g., 'products', 'inventory'

    # Filter configuration
    filters = Column(JSONB, nullable=False)  # Filter conditions as JSON
    is_default = Column(Boolean, default=False, nullable=False)  # Default filter for module

    # Ownership and sharing
    created_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_shared = Column(Boolean, default=False, nullable=False)  # Whether filter is shared

    # Timestamps
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
        Index("idx_saved_filters_tenant_module", "tenant_id", "module"),
        Index("idx_saved_filters_user", "tenant_id", "created_by"),
    )

    def __repr__(self) -> str:
        return f"<SavedFilter(id={self.id}, name={self.name}, module={self.module})>"


class CustomView(Base):
    """Custom view model for personalized view configurations."""

    __tablename__ = "custom_views"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # View information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    module = Column(String(50), nullable=False, index=True)  # e.g., 'products', 'inventory'

    # View configuration
    columns = Column(JSONB, nullable=False)  # Column configuration (visible, order, width, etc.)
    sorting = Column(JSONB, nullable=True)  # Sorting configuration
    grouping = Column(JSONB, nullable=True)  # Grouping configuration
    filters = Column(JSONB, nullable=True)  # Associated filters

    # Settings
    is_default = Column(Boolean, default=False, nullable=False)  # Default view for module
    is_shared = Column(Boolean, default=False, nullable=False)  # Whether view is shared

    # Ownership
    created_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Timestamps
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
        Index("idx_custom_views_tenant_module", "tenant_id", "module"),
        Index("idx_custom_views_user", "tenant_id", "created_by"),
    )

    def __repr__(self) -> str:
        return f"<CustomView(id={self.id}, name={self.name}, module={self.module})>"


class ViewShare(Base):
    """View share model for sharing filters and views with other users."""

    __tablename__ = "view_shares"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Share information
    filter_id = Column(PG_UUID(as_uuid=True), nullable=True)  # Shared filter ID
    view_id = Column(PG_UUID(as_uuid=True), nullable=True)  # Shared view ID

    # Shared with
    shared_with_user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    shared_with_role = Column(String(50), nullable=True)  # Shared with role (future)

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_view_shares_filter", "tenant_id", "filter_id"),
        Index("idx_view_shares_view", "tenant_id", "view_id"),
        Index("idx_view_shares_user", "tenant_id", "shared_with_user_id"),
    )

    def __repr__(self) -> str:
        return f"<ViewShare(id={self.id}, filter_id={self.filter_id}, view_id={self.view_id})>"







