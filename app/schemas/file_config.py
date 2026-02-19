"""Pydantic schemas for file configuration."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class S3ConfigBase(BaseModel):
    """Base S3 configuration schema."""

    bucket_name: str = Field(..., description="S3 bucket name")
    access_key_id: str = Field(..., description="AWS access key ID")
    secret_access_key: str = Field(..., description="AWS secret access key")
    region: str = Field(default="us-east-1", description="AWS region")


class S3ConfigResponse(BaseModel):
    """S3 configuration response (secret is hidden)."""

    bucket_name: str
    access_key_id: str
    secret_access_key: str = Field(default="***", description="Secret is never returned")
    region: str

    model_config = ConfigDict(from_attributes=True)


class LocalConfigBase(BaseModel):
    """Local storage configuration schema."""

    base_path: str = Field(default="./storage", description="Base path for local storage")


class StorageConfigResponse(BaseModel):
    """Storage configuration response."""

    backend: str = Field(..., description="Storage backend: 'local', 's3', or 'hybrid'")
    s3: S3ConfigResponse | None = Field(None, description="S3 configuration (if applicable)")
    local: LocalConfigBase | None = Field(None, description="Local storage configuration (if applicable)")

    model_config = ConfigDict(from_attributes=True)


class StorageConfigUpdate(BaseModel):
    """Storage configuration update request."""

    backend: str = Field(..., description="Storage backend: 'local', 's3', or 'hybrid'")
    s3: dict[str, Any] | None = Field(None, description="S3 configuration (required if backend is 's3' or 'hybrid')")
    local: dict[str, Any] | None = Field(None, description="Local storage configuration (required if backend is 'local' or 'hybrid')")


class S3ConnectionTestRequest(BaseModel):
    """S3 connection test request."""

    bucket_name: str = Field(..., description="S3 bucket name")
    access_key_id: str = Field(..., description="AWS access key ID")
    secret_access_key: str = Field(..., description="AWS secret access key")
    region: str = Field(default="us-east-1", description="AWS region")


class S3ConnectionTestResponse(BaseModel):
    """S3 connection test response."""

    success: bool
    message: str
    bucket_name: str | None = None
    region: str | None = None

    model_config = ConfigDict(from_attributes=True)


class StorageStatsResponse(BaseModel):
    """Storage statistics response."""

    total_space_used: int = Field(..., description="Total space used in bytes")
    total_files: int = Field(..., description="Total number of files")
    total_versions: int = Field(..., description="Total number of file versions")
    total_folders: int = Field(..., description="Total number of folders")
    mime_distribution: dict[str, int] = Field(default_factory=dict, description="Distribution of files by MIME type")
    entity_distribution: dict[str, int] = Field(default_factory=dict, description="Distribution of files by entity type")
    files_with_permissions: int = Field(..., description="Number of files with permissions assigned")
    folders_with_permissions: int = Field(..., description="Number of folders with permissions assigned")
    file_permission_distribution: dict[str, int] = Field(default_factory=dict, description="Distribution of file permissions by target type")
    folder_permission_distribution: dict[str, int] = Field(default_factory=dict, description="Distribution of folder permissions by target type")

    model_config = ConfigDict(from_attributes=True)


class FileLimitsResponse(BaseModel):
    """File limits configuration response."""

    max_file_size: int = Field(..., description="Maximum file size in bytes")
    allowed_mime_types: list[str] = Field(default_factory=list, description="Allowed MIME types (empty = all allowed)")
    blocked_mime_types: list[str] = Field(default_factory=list, description="Blocked MIME types")
    max_versions_per_file: int = Field(..., description="Maximum versions per file")
    retention_days: int | None = Field(None, description="File retention period in days (None = no limit)")

    model_config = ConfigDict(from_attributes=True)


class FileLimitsUpdate(BaseModel):
    """File limits configuration update request."""

    max_file_size: int | None = Field(None, description="Maximum file size in bytes")
    allowed_mime_types: list[str] | None = Field(None, description="Allowed MIME types (empty = all allowed)")
    blocked_mime_types: list[str] | None = Field(None, description="Blocked MIME types")
    max_versions_per_file: int | None = Field(None, description="Maximum versions per file")
    retention_days: int | None = Field(None, description="File retention period in days (None = no limit)")


class ThumbnailConfigResponse(BaseModel):
    """Thumbnail configuration response."""

    default_width: int = Field(..., description="Default thumbnail width in pixels")
    default_height: int = Field(..., description="Default thumbnail height in pixels")
    quality: int = Field(..., description="JPEG quality (1-100)")
    cache_enabled: bool = Field(..., description="Whether thumbnail cache is enabled")
    max_cache_size: int = Field(..., description="Maximum cache size in bytes")

    model_config = ConfigDict(from_attributes=True)


class ThumbnailConfigUpdate(BaseModel):
    """Thumbnail configuration update request."""

    default_width: int | None = Field(None, description="Default thumbnail width in pixels")
    default_height: int | None = Field(None, description="Default thumbnail height in pixels")
    quality: int | None = Field(None, description="JPEG quality (1-100)")
    cache_enabled: bool | None = Field(None, description="Whether thumbnail cache is enabled")
    max_cache_size: int | None = Field(None, description="Maximum cache size in bytes")

