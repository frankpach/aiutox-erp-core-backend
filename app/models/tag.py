"""Tag models for tagging system."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.core.db.session import Base


class Tag(Base):
    """Tag model for tagging entities."""

    __tablename__ = "tags"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Tag information
    name = Column(String(100), nullable=False, index=True)
    color = Column(String(7), nullable=True)  # Hex color code (e.g., #FF5733)
    description = Column(String(500), nullable=True)

    # Category (optional hierarchy)
    category_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tag_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Metadata
    is_active = Column(Boolean, default=True, nullable=False, index=True)

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
        Index("idx_tags_tenant_name", "tenant_id", "name", unique=True),
        Index("idx_tags_category", "tenant_id", "category_id"),
    )

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name={self.name}, tenant_id={self.tenant_id})>"


class TagCategory(Base):
    """Tag category model for organizing tags."""

    __tablename__ = "tag_categories"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Category information
    name = Column(String(100), nullable=False)
    color = Column(String(7), nullable=True)  # Hex color code
    description = Column(String(500), nullable=True)

    # Hierarchy (optional parent category)
    parent_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tag_categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Ordering
    sort_order = Column(Integer, default=0, nullable=False)

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
        Index("idx_tag_categories_tenant_name", "tenant_id", "name", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<TagCategory(id={self.id}, name={self.name}, tenant_id={self.tenant_id})>"
        )


class EntityTag(Base):
    """Entity tag relationship model (polymorphic many-to-many)."""

    __tablename__ = "entity_tags"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Tag reference
    tag_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Polymorphic relationship
    entity_type = Column(
        String(50), nullable=False, index=True
    )  # e.g., 'product', 'order'
    entity_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_entity_tags_entity", "entity_type", "entity_id"),
        Index("idx_entity_tags_tag", "tag_id"),
        Index("idx_entity_tags_tenant_entity", "tenant_id", "entity_type", "entity_id"),
        Index(
            "idx_entity_tags_unique", "tag_id", "entity_type", "entity_id", unique=True
        ),
    )

    def __repr__(self) -> str:
        return f"<EntityTag(id={self.id}, tag_id={self.tag_id}, entity={self.entity_type}:{self.entity_id})>"
