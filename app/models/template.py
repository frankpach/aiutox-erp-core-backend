"""Template models for document and notification template management."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class TemplateType(str, Enum):
    """Template types."""

    DOCUMENT = "document"  # PDF, HTML documents
    EMAIL = "email"  # Email templates
    SMS = "sms"  # SMS templates
    NOTIFICATION = "notification"  # In-app notifications


class TemplateFormat(str, Enum):
    """Template formats."""

    HTML = "html"
    PDF = "pdf"
    TEXT = "text"
    MARKDOWN = "markdown"


class Template(Base):
    """Template model for reusable templates."""

    __tablename__ = "templates"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Template information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    template_type = Column(String(20), nullable=False)  # document, email, sms, notification
    template_format = Column(String(20), nullable=False)  # html, pdf, text, markdown
    category = Column(String(50), nullable=True, index=True)  # Template category

    # Template content
    content = Column(Text, nullable=False)  # Template content (Jinja2, etc.)
    variables = Column(JSONB, nullable=True)  # Available variables and their types

    # Settings
    is_active = Column(Boolean, default=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)  # System template (cannot be deleted)

    # Ownership
    created_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Metadata
    meta_data = Column("metadata", JSONB, nullable=True)

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

    # Relationships
    versions = relationship("TemplateVersion", back_populates="template", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_templates_tenant_type", "tenant_id", "template_type"),
        Index("idx_templates_category", "tenant_id", "category"),
    )

    def __repr__(self) -> str:
        return f"<Template(id={self.id}, name={self.name}, type={self.template_type})>"


class TemplateVersion(Base):
    """Template version model for versioning templates."""

    __tablename__ = "template_versions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Template relationship
    template_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Version information
    version_number = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    content = Column(Text, nullable=False)  # Template content for this version
    variables = Column(JSONB, nullable=True)  # Variables for this version
    changelog = Column(Text, nullable=True)  # What changed in this version

    # Status
    is_current = Column(Boolean, default=True, nullable=False, index=True)  # Current version

    # Created by
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

    # Relationships
    template = relationship("Template", back_populates="versions")

    __table_args__ = (
        Index("idx_template_versions_template", "template_id", "version_number"),
        Index("idx_template_versions_current", "template_id", "is_current"),
    )

    def __repr__(self) -> str:
        return f"<TemplateVersion(id={self.id}, template_id={self.template_id}, version={self.version_number})>"


class TemplateCategory(Base):
    """Template category model for organizing templates."""

    __tablename__ = "template_categories"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Category information
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    parent_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("template_categories.id", ondelete="SET NULL"),
        nullable=True,
    )  # For hierarchical categories

    # Settings
    is_active = Column(Boolean, default=True, nullable=False)

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
        Index("idx_template_categories_tenant", "tenant_id", "name"),
    )

    def __repr__(self) -> str:
        return f"<TemplateCategory(id={self.id}, name={self.name})>"








