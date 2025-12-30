"""Import/Export service for data import and export management."""

import csv
import io
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.files.service import FileService
from app.core.pubsub import EventPublisher, get_event_publisher
from app.core.pubsub.models import EventMetadata
from app.models.import_export import ExportFormat, ExportJob, ImportJob, ImportStatus
from app.repositories.import_export_repository import ImportExportRepository

logger = logging.getLogger(__name__)


class DataExporter:
    """Service for exporting data to various formats."""

    def __init__(self, db: Session):
        """Initialize exporter with database session."""
        self.db = db

    def export_to_csv(
        self, data: list[dict[str, Any]], columns: list[str] | None = None
    ) -> bytes:
        """Export data to CSV format.

        Args:
            data: List of dictionaries representing rows
            columns: List of column names to export (if None, uses all keys from first row)

        Returns:
            CSV data as bytes
        """
        if not data:
            return b""

        # Determine columns
        if columns is None:
            columns = list(data[0].keys())

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)

        return output.getvalue().encode("utf-8")

    def export_to_excel(
        self, data: list[dict[str, Any]], columns: list[str] | None = None
    ) -> bytes:
        """Export data to Excel format.

        Args:
            data: List of dictionaries representing rows
            columns: List of column names to export

        Returns:
            Excel data as bytes
        """
        try:
            from openpyxl import Workbook

            wb = Workbook()
            ws = wb.active

            if not data:
                return b""

            # Determine columns
            if columns is None:
                columns = list(data[0].keys())

            # Write header
            ws.append(columns)

            # Write data
            for row in data:
                ws.append([row.get(col, "") for col in columns])

            # Save to bytes
            output = io.BytesIO()
            wb.save(output)
            return output.getvalue()

        except ImportError:
            logger.error("openpyxl not installed, cannot export to Excel")
            raise ValueError("Excel export requires openpyxl package")

    def export_to_pdf(
        self, data: list[dict[str, Any]], columns: list[str] | None = None, title: str = "Export"
    ) -> bytes:
        """Export data to PDF format.

        Args:
            data: List of dictionaries representing rows
            columns: List of column names to export
            title: PDF title

        Returns:
            PDF data as bytes
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

            if not data:
                return b""

            # Determine columns
            if columns is None:
                columns = list(data[0].keys())

            # Create PDF in memory
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []

            # Create table data
            table_data = [columns]  # Header
            for row in data:
                table_data.append([str(row.get(col, "")) for col in columns])

            # Create table
            table = Table(table_data)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 14),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )

            elements.append(table)
            doc.build(elements)

            return buffer.getvalue()

        except ImportError:
            logger.error("reportlab not installed, cannot export to PDF")
            raise ValueError("PDF export requires reportlab package")


class DataImporter:
    """Service for importing data from various formats."""

    def __init__(self, db: Session):
        """Initialize importer with database session."""
        self.db = db

    def import_from_csv(
        self,
        file_content: bytes,
        delimiter: str = ",",
        encoding: str = "utf-8",
        skip_header: bool = True,
    ) -> list[dict[str, Any]]:
        """Import data from CSV format.

        Args:
            file_content: CSV file content as bytes
            delimiter: CSV delimiter
            encoding: File encoding
            skip_header: Whether to skip the first row (header)

        Returns:
            List of dictionaries representing rows
        """
        try:
            content = file_content.decode(encoding)
            reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)

            data = []
            for row in reader:
                # Convert empty strings to None
                cleaned_row = {k: (v if v else None) for k, v in row.items()}
                data.append(cleaned_row)

            return data

        except Exception as e:
            logger.error(f"Failed to import CSV: {e}")
            raise ValueError(f"Failed to parse CSV file: {e}")

    def validate_data(
        self, data: list[dict[str, Any]], validation_rules: dict[str, Any] | None = None
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Validate imported data.

        Args:
            data: List of dictionaries representing rows
            validation_rules: Validation rules (optional)

        Returns:
            Tuple of (valid_rows, invalid_rows_with_errors)
        """
        valid_rows = []
        invalid_rows = []

        for idx, row in enumerate(data):
            errors = []
            # Basic validation (can be extended with validation_rules)
            if validation_rules:
                for field, rules in validation_rules.items():
                    value = row.get(field)
                    if "required" in rules and rules["required"] and not value:
                        errors.append(f"{field} is required")
                    if "type" in rules and value:
                        expected_type = rules["type"]
                        if expected_type == "int" and not isinstance(value, int):
                            try:
                                int(value)
                            except (ValueError, TypeError):
                                errors.append(f"{field} must be an integer")

            if errors:
                invalid_rows.append({"row": idx + 1, "data": row, "errors": errors})
            else:
                valid_rows.append(row)

        return valid_rows, invalid_rows


class ImportExportService:
    """Service for managing import and export operations."""

    def __init__(
        self,
        db: Session,
        file_service: FileService | None = None,
        event_publisher: EventPublisher | None = None,
    ):
        """Initialize import/export service.

        Args:
            db: Database session
            file_service: FileService instance (created if not provided)
            event_publisher: EventPublisher instance (created if not provided)
        """
        self.db = db
        self.repository = ImportExportRepository(db)
        self.exporter = DataExporter(db)
        self.importer = DataImporter(db)
        self.file_service = file_service or FileService(db)
        self.event_publisher = event_publisher or get_event_publisher()

    def create_import_job(
        self,
        job_data: dict,
        tenant_id: UUID,
        user_id: UUID,
    ) -> ImportJob:
        """Create a new import job.

        Args:
            job_data: Import job data
            tenant_id: Tenant ID
            user_id: User ID who created the job

        Returns:
            Created ImportJob object
        """
        job_data["tenant_id"] = tenant_id
        job_data["created_by"] = user_id
        job_data["status"] = ImportStatus.PENDING

        job = self.repository.create_import_job(job_data)

        # Publish event
        from app.core.pubsub.event_helpers import safe_publish_event

        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="import.started",
            entity_type="import_job",
            entity_id=job.id,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=EventMetadata(
                source="import_export_service",
                version="1.0",
                additional_data={"module": job.module, "file_name": job.file_name},
            ),
        )

        return job

    def create_export_job(
        self,
        job_data: dict,
        tenant_id: UUID,
        user_id: UUID,
    ) -> ExportJob:
        """Create a new export job.

        Args:
            job_data: Export job data
            tenant_id: Tenant ID
            user_id: User ID who created the job

        Returns:
            Created ExportJob object
        """
        job_data["tenant_id"] = tenant_id
        job_data["created_by"] = user_id
        job_data["status"] = ImportStatus.PENDING

        return self.repository.create_export_job(job_data)

    def get_import_job(self, job_id: UUID, tenant_id: UUID) -> ImportJob | None:
        """Get import job by ID."""
        return self.repository.get_import_job_by_id(job_id, tenant_id)

    def get_export_job(self, job_id: UUID, tenant_id: UUID) -> ExportJob | None:
        """Get export job by ID."""
        return self.repository.get_export_job_by_id(job_id, tenant_id)

    def create_import_template(
        self,
        template_data: dict,
        tenant_id: UUID,
        user_id: UUID,
    ) -> Any:
        """Create a new import template."""
        template_data["tenant_id"] = tenant_id
        template_data["created_by"] = user_id
        return self.repository.create_import_template(template_data)

    def get_import_template(self, template_id: UUID, tenant_id: UUID) -> Any:
        """Get import template by ID."""
        return self.repository.get_import_template_by_id(template_id, tenant_id)

    def get_import_templates(
        self, tenant_id: UUID, module: str | None = None, skip: int = 0, limit: int = 100
    ) -> list[Any]:
        """Get import templates."""
        return self.repository.get_import_templates(tenant_id, module, skip, limit)

    def count_import_jobs(
        self,
        tenant_id: UUID,
        module: str | None = None,
        status: str | None = None,
    ) -> int:
        """Count import jobs with optional filters."""
        return self.repository.count_import_jobs(tenant_id, module, status)

    def count_export_jobs(
        self,
        tenant_id: UUID,
        module: str | None = None,
        status: str | None = None,
    ) -> int:
        """Count export jobs with optional filters."""
        return self.repository.count_export_jobs(tenant_id, module, status)

    def count_import_templates(
        self,
        tenant_id: UUID,
        module: str | None = None,
    ) -> int:
        """Count import templates with optional filters."""
        return self.repository.count_import_templates(tenant_id, module)





