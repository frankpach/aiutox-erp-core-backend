"""Folder model for organizing files in a hierarchical structure."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class Folder(Base):
    """Folder model for organizing files in a hierarchical structure."""

    __tablename__ = "folders"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Folder information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Hex color for folder icon (e.g., #FF5733)
    icon = Column(String(50), nullable=True)  # Icon name (e.g., "folder", "folder-documents")

    # Hierarchical structure
    parent_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("folders.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Organization
    entity_type = Column(String(50), nullable=True, index=True)  # e.g., 'product', 'order'
    entity_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)

    # Metadata
    folder_metadata = Column("metadata", JSONB, nullable=True)  # Additional metadata as JSON

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
        index=True,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    parent = relationship("Folder", remote_side=[id], backref="children")
    files = relationship("File", backref="folder", lazy="dynamic")

    __table_args__ = (
        Index("idx_folders_tenant_parent", "tenant_id", "parent_id"),
        Index("idx_folders_entity", "entity_type", "entity_id"),
        Index("idx_folders_tenant_entity", "tenant_id", "entity_type", "entity_id"),
        Index("idx_folders_name", "tenant_id", "parent_id", "name"),  # For unique folder names per parent
    )

    def __repr__(self) -> str:
        return f"<Folder(id={self.id}, name={self.name}, tenant_id={self.tenant_id}, parent_id={self.parent_id})>"

    def get_path(self) -> str:
        """Get the full path of the folder (e.g., /Root/Documents/Projects)."""
        path_parts = [self.name]
        current = self.parent
        while current:
            path_parts.insert(0, current.name)
            current = current.parent
        return "/" + "/".join(path_parts)

    def get_depth(self) -> int:
        """Get the depth of the folder in the hierarchy (0 for root folders)."""
        depth = 0
        current = self.parent
        while current:
            depth += 1
            current = current.parent
        return depth


