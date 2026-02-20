"""Preference models for user personalization."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.core.db.session import Base


class UserPreference(Base):
    """User preference model."""

    __tablename__ = "user_preferences"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    preference_type = Column(
        String(50), nullable=False, index=True
    )  # e.g., 'basic', 'notification', 'view'
    key = Column(String(255), nullable=False)
    value = Column(JSONB, nullable=False)
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
        Index(
            "idx_user_preferences_user_type_key",
            "user_id",
            "preference_type",
            "key",
            unique=True,
        ),
        Index("idx_user_preferences_tenant", "tenant_id"),
    )


class OrgPreference(Base):
    """Organization preference model."""

    __tablename__ = "org_preferences"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    preference_type = Column(String(50), nullable=False, index=True)
    key = Column(String(255), nullable=False)
    value = Column(JSONB, nullable=False)
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
        Index(
            "idx_org_preferences_tenant_type_key",
            "tenant_id",
            "preference_type",
            "key",
            unique=True,
        ),
    )


class RolePreference(Base):
    """Role preference model."""

    __tablename__ = "role_preferences"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    role_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("module_roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    preference_type = Column(String(50), nullable=False, index=True)
    key = Column(String(255), nullable=False)
    value = Column(JSONB, nullable=False)
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
        Index(
            "idx_role_preferences_role_type_key",
            "role_id",
            "preference_type",
            "key",
            unique=True,
        ),
        Index("idx_role_preferences_tenant", "tenant_id"),
    )


class SavedView(Base):
    """Saved view model for user custom views."""

    __tablename__ = "saved_views"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    module = Column(
        String(100), nullable=False, index=True
    )  # e.g., 'products', 'inventory'
    name = Column(String(255), nullable=False)
    config = Column(
        JSONB, nullable=False
    )  # View configuration (columns, filters, sorting, etc.)
    is_default = Column(Boolean, default=False, nullable=False)
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
        Index("idx_saved_views_user_module", "user_id", "module"),
        Index("idx_saved_views_tenant", "tenant_id"),
    )


class Dashboard(Base):
    """Dashboard model for user custom dashboards."""

    __tablename__ = "dashboards"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    widgets = Column(JSONB, nullable=False)  # Array of widget configurations
    is_default = Column(Boolean, default=False, nullable=False)
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
        Index("idx_dashboards_user", "user_id"),
        Index("idx_dashboards_tenant", "tenant_id"),
    )
