"""Import/Export models for data import and export management."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.core.db.session import Base


class ExportFormat(str, Enum):
    """Export formats."""

    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"


class ImportStatus(str, Enum):
    """Import job status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImportJob(Base):
    """Import job model for tracking import operations."""

    __tablename__ = "import_jobs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Job information
    module = Column(String(50), nullable=False, index=True)  # e.g., 'products', 'inventory'
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)  # Path to uploaded file
    file_size = Column(Integer, nullable=True)  # Size in bytes

    # Import configuration
    template_id = Column(PG_UUID(as_uuid=True), nullable=True)  # Import template ID (future)
    mapping = Column(JSONB, nullable=True)  # Field mapping configuration
    options = Column(JSONB, nullable=True)  # Import options (skip_errors, etc.)

    # Status and progress
    status = Column(String(20), nullable=False, default=ImportStatus.PENDING, index=True)
    progress = Column(Integer, default=0, nullable=False)  # 0-100
    total_rows = Column(Integer, nullable=True)
    processed_rows = Column(Integer, default=0, nullable=False)
    successful_rows = Column(Integer, default=0, nullable=False)
    failed_rows = Column(Integer, default=0, nullable=False)

    # Results
    errors = Column(JSONB, nullable=True)  # List of errors encountered
    warnings = Column(JSONB, nullable=True)  # List of warnings
    result_summary = Column(JSONB, nullable=True)  # Summary of import results

    # User who initiated the import
    created_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Timestamps
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
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
        Index("idx_import_jobs_tenant_status", "tenant_id", "status"),
        Index("idx_import_jobs_module", "tenant_id", "module"),
    )

    def __repr__(self) -> str:
        return f"<ImportJob(id={self.id}, module={self.module}, status={self.status})>"


class ImportTemplate(Base):
    """Import template model for reusable import configurations."""

    __tablename__ = "import_templates"

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
    module = Column(String(50), nullable=False, index=True)  # e.g., 'products', 'inventory'

    # Template configuration
    field_mapping = Column(JSONB, nullable=False)  # CSV column -> model field mapping
    default_values = Column(JSONB, nullable=True)  # Default values for fields
    validation_rules = Column(JSONB, nullable=True)  # Validation rules
    transformations = Column(JSONB, nullable=True)  # Data transformations

    # Settings
    skip_header = Column(Boolean, default=True, nullable=False)
    delimiter = Column(String(1), default=",", nullable=False)
    encoding = Column(String(20), default="utf-8", nullable=False)

    # User who created the template
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
        Index("idx_import_templates_tenant_module", "tenant_id", "module"),
    )

    def __repr__(self) -> str:
        return f"<ImportTemplate(id={self.id}, name={self.name}, module={self.module})>"


class ExportJob(Base):
    """Export job model for tracking export operations."""

    __tablename__ = "export_jobs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Job information
    module = Column(String(50), nullable=False, index=True)  # e.g., 'products', 'inventory'
    export_format = Column(String(20), nullable=False)  # csv, excel, pdf
    file_name = Column(String(255), nullable=True)  # Generated file name
    file_path = Column(String(500), nullable=True)  # Path to exported file
    file_size = Column(Integer, nullable=True)  # Size in bytes

    # Export configuration
    filters = Column(JSONB, nullable=True)  # Export filters
    columns = Column(JSONB, nullable=True)  # Columns to export
    options = Column(JSONB, nullable=True)  # Export options

    # Status
    status = Column(String(20), nullable=False, default=ImportStatus.PENDING, index=True)
    total_rows = Column(Integer, nullable=True)
    exported_rows = Column(Integer, default=0, nullable=False)

    # User who initiated the export
    created_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Timestamps
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
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
        Index("idx_export_jobs_tenant_status", "tenant_id", "status"),
        Index("idx_export_jobs_module", "tenant_id", "module"),
    )

    def __repr__(self) -> str:
        return f"<ExportJob(id={self.id}, module={self.module}, format={self.export_format})>"








