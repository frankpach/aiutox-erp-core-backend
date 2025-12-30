"""File models for file and document management."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class StorageBackend(str, Enum):
    """Storage backend types."""

    LOCAL = "local"
    S3 = "s3"
    HYBRID = "hybrid"


class FileEntityType(str, Enum):
    """Entity types that can have files attached."""

    PRODUCT = "product"
    ORGANIZATION = "organization"
    CONTACT = "contact"
    USER = "user"
    ORDER = "order"
    INVOICE = "invoice"
    ACTIVITY = "activity"
    TASK = "task"
    # Add more as needed


class File(Base):
    """File model for storing file information."""

    __tablename__ = "files"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File information
    name = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)  # Original filename from upload
    mime_type = Column(String(100), nullable=False)
    size = Column(Integer, nullable=False)  # Size in bytes
    extension = Column(String(10), nullable=True)  # File extension (e.g., .pdf, .jpg)

    # Storage information
    storage_backend = Column(
        String(20), nullable=False, default=StorageBackend.LOCAL
    )  # local, s3, hybrid
    storage_path = Column(String(500), nullable=False)  # Path in storage (local path or S3 key)
    storage_url = Column(String(1000), nullable=True)  # Public URL if available

    # Folder relationship
    folder_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("folders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Polymorphic relationship
    entity_type = Column(String(50), nullable=True, index=True)  # e.g., 'product', 'order'
    entity_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)

    # Metadata
    description = Column(Text, nullable=True)
    # Use explicit column name to avoid conflict with SQLAlchemy's reserved 'metadata'
    file_metadata = Column("metadata", JSONB, nullable=True)  # Additional metadata as JSON

    # Versioning
    version_number = Column(Integer, default=1, nullable=False)
    is_current = Column(Boolean, default=True, nullable=False, index=True)

    # Ownership
    uploaded_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationship to user
    uploaded_by_user = relationship("User", foreign_keys=[uploaded_by], lazy="select")

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
        Index("idx_files_entity", "entity_type", "entity_id"),
        Index("idx_files_tenant_entity", "tenant_id", "entity_type", "entity_id"),
        Index("idx_files_current", "tenant_id", "is_current"),
    )

    def __repr__(self) -> str:
        return f"<File(id={self.id}, name={self.name}, tenant_id={self.tenant_id})>"


class FileVersion(Base):
    """File version model for tracking file versions."""

    __tablename__ = "file_versions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    file_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Version information
    version_number = Column(Integer, nullable=False)
    storage_path = Column(String(500), nullable=False)
    storage_backend = Column(String(20), nullable=False)
    size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)

    # Version metadata
    change_description = Column(Text, nullable=True)  # Description of changes in this version
    created_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("idx_file_versions_file", "file_id", "version_number"),
    )

    def __repr__(self) -> str:
        return f"<FileVersion(id={self.id}, file_id={self.file_id}, version={self.version_number})>"


class FilePermission(Base):
    """File permission model for access control."""

    __tablename__ = "file_permissions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    file_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Permission target (polymorphic)
    # Can be user, role, or organization
    target_type = Column(String(50), nullable=False)  # 'user', 'role', 'organization'
    target_id = Column(PG_UUID(as_uuid=True), nullable=False)

    # Permissions
    can_view = Column(Boolean, default=True, nullable=False)
    can_download = Column(Boolean, default=True, nullable=False)
    can_edit = Column(Boolean, default=False, nullable=False)
    can_delete = Column(Boolean, default=False, nullable=False)

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
        Index("idx_file_permissions_file", "file_id"),
        Index("idx_file_permissions_target", "target_type", "target_id"),
        Index("idx_file_permissions_tenant", "tenant_id", "target_type", "target_id"),
    )

    def __repr__(self) -> str:
        return f"<FilePermission(id={self.id}, file_id={self.file_id}, target={self.target_type}:{self.target_id})>"

