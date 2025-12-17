"""Import/Export schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Import Job schemas
class ImportJobBase(BaseModel):
    """Base schema for import job."""

    module: str = Field(..., description="Module name (e.g., 'products', 'inventory')", max_length=50)
    file_name: str = Field(..., description="File name", max_length=255)
    template_id: UUID | None = Field(None, description="Import template ID")
    mapping: dict[str, Any] | None = Field(None, description="Field mapping configuration")
    options: dict[str, Any] | None = Field(None, description="Import options")


class ImportJobCreate(ImportJobBase):
    """Schema for creating an import job."""

    pass


class ImportJobResponse(ImportJobBase):
    """Schema for import job response."""

    id: UUID
    tenant_id: UUID
    file_path: str | None
    file_size: int | None
    status: str
    progress: int
    total_rows: int | None
    processed_rows: int
    successful_rows: int
    failed_rows: int
    errors: list[dict[str, Any]] | None
    warnings: list[dict[str, Any]] | None
    result_summary: dict[str, Any] | None
    created_by: UUID | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Import Template schemas
class ImportTemplateBase(BaseModel):
    """Base schema for import template."""

    name: str = Field(..., description="Template name", max_length=255)
    description: str | None = Field(None, description="Template description")
    module: str = Field(..., description="Module name", max_length=50)
    field_mapping: dict[str, Any] = Field(..., description="Field mapping configuration")
    default_values: dict[str, Any] | None = Field(None, description="Default values for fields")
    validation_rules: dict[str, Any] | None = Field(None, description="Validation rules")
    transformations: dict[str, Any] | None = Field(None, description="Data transformations")
    skip_header: bool = Field(True, description="Skip header row")
    delimiter: str = Field(",", description="CSV delimiter", max_length=1)
    encoding: str = Field("utf-8", description="File encoding", max_length=20)


class ImportTemplateCreate(ImportTemplateBase):
    """Schema for creating an import template."""

    pass


class ImportTemplateUpdate(BaseModel):
    """Schema for updating an import template."""

    name: str | None = Field(None, description="Template name", max_length=255)
    description: str | None = Field(None, description="Template description")
    field_mapping: dict[str, Any] | None = Field(None, description="Field mapping configuration")
    default_values: dict[str, Any] | None = Field(None, description="Default values for fields")
    validation_rules: dict[str, Any] | None = Field(None, description="Validation rules")
    transformations: dict[str, Any] | None = Field(None, description="Data transformations")
    skip_header: bool | None = Field(None, description="Skip header row")
    delimiter: str | None = Field(None, description="CSV delimiter", max_length=1)
    encoding: str | None = Field(None, description="File encoding", max_length=20)


class ImportTemplateResponse(ImportTemplateBase):
    """Schema for import template response."""

    id: UUID
    tenant_id: UUID
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Export Job schemas
class ExportJobBase(BaseModel):
    """Base schema for export job."""

    module: str = Field(..., description="Module name (e.g., 'products', 'inventory')", max_length=50)
    export_format: str = Field(..., description="Export format (csv, excel, pdf)", max_length=20)
    filters: dict[str, Any] | None = Field(None, description="Export filters")
    columns: list[str] | None = Field(None, description="Columns to export")
    options: dict[str, Any] | None = Field(None, description="Export options")


class ExportJobCreate(ExportJobBase):
    """Schema for creating an export job."""

    pass


class ExportJobResponse(ExportJobBase):
    """Schema for export job response."""

    id: UUID
    tenant_id: UUID
    file_name: str | None
    file_path: str | None
    file_size: int | None
    status: str
    total_rows: int | None
    exported_rows: int
    created_by: UUID | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)







