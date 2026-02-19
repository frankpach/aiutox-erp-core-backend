"""Search index models for global search functionality."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.core.db.session import Base


class SearchIndex(Base):
    """Search index model for indexing entities for global search."""

    __tablename__ = "search_indices"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Entity reference (polymorphic)
    entity_type = Column(String(50), nullable=False, index=True)  # e.g., 'product', 'contact', 'order'
    entity_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)

    # Searchable content
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)  # Full text content for search
    search_vector = Column(TSVECTOR, nullable=True)  # PostgreSQL full-text search vector

    # Additional searchable fields (stored as JSON for flexibility)
    search_metadata = Column("metadata", Text, nullable=True)  # JSON string with additional searchable fields

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_search_indices_entity", "entity_type", "entity_id", unique=True),
        Index("idx_search_indices_tenant_entity", "tenant_id", "entity_type", "entity_id"),
        Index("idx_search_indices_vector", "search_vector", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<SearchIndex(id={self.id}, entity_type={self.entity_type}, entity_id={self.entity_id})>"

