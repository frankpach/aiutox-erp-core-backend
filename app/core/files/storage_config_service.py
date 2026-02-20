"""Storage configuration service for managing file storage settings."""

import logging
import re
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config.service import ConfigService
from app.core.exceptions import APIException
from app.core.files.storage import S3StorageBackend
from app.core.security.encryption import encrypt_credentials

logger = logging.getLogger(__name__)

# AWS S3 valid regions
AWS_VALID_REGIONS = [
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2",
    "eu-west-1",
    "eu-west-2",
    "eu-west-3",
    "eu-central-1",
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-northeast-1",
    "ap-northeast-2",
    "ap-south-1",
    "sa-east-1",
    "ca-central-1",
    "eu-north-1",
    "ap-east-1",
    "me-south-1",
    "af-south-1",
    "eu-south-1",
    "ap-northeast-3",
    "us-gov-east-1",
    "us-gov-west-1",
]

# MIME type pattern validation
MIME_TYPE_PATTERN = re.compile(
    r"^[a-z]+/[a-z0-9][a-z0-9!#$&\-\^_.]*$|^\*/\*$|^[a-z]+/\*$"
)


class StorageConfigService:
    """Service for managing storage configuration."""

    def __init__(self, db: Session):
        """Initialize storage config service.

        Args:
            db: Database session
        """
        self.db = db
        self.config_service = ConfigService(db, use_cache=True, use_versioning=True)
        self.module = "files"

    def get_storage_config(self, tenant_id: UUID) -> dict[str, Any]:
        """Get current storage configuration.

        Args:
            tenant_id: Tenant ID

        Returns:
            Dictionary with storage configuration
        """
        backend = self.config_service.get(
            tenant_id, self.module, "storage.backend", "local"
        )
        config: dict[str, Any] = {
            "backend": backend,
        }

        if backend in ("s3", "hybrid"):
            # Get S3 configuration (credentials are encrypted)
            config["s3"] = {
                "bucket_name": self.config_service.get(
                    tenant_id, self.module, "storage.s3.bucket_name", ""
                ),
                "access_key_id": self.config_service.get(
                    tenant_id, self.module, "storage.s3.access_key_id", ""
                ),
                "secret_access_key": "***",  # Never return actual secret
                "region": self.config_service.get(
                    tenant_id, self.module, "storage.s3.region", "us-east-1"
                ),
            }

        if backend in ("local", "hybrid"):
            config["local"] = {
                "base_path": self.config_service.get(
                    tenant_id, self.module, "storage.local.base_path", "./storage"
                ),
            }

        return config

    def update_storage_config(
        self,
        tenant_id: UUID,
        config: dict[str, Any],
        user_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Update storage configuration.

        Args:
            tenant_id: Tenant ID
            config: Configuration dictionary
            user_id: User ID making the change
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Updated configuration dictionary

        Raises:
            APIException: If configuration is invalid
        """
        backend = config.get("backend", "local")
        if backend not in ("local", "s3", "hybrid"):
            raise APIException(
                status_code=400,
                code="INVALID_BACKEND",
                message=f"Invalid backend: {backend}. Must be 'local', 's3', or 'hybrid'",
            )

        # Update backend
        self.config_service.set(
            tenant_id=tenant_id,
            module=self.module,
            key="storage.backend",
            value=backend,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Update S3 configuration if needed
        if backend in ("s3", "hybrid"):
            s3_config = config.get("s3", {})
            bucket_name = s3_config.get("bucket_name", "")
            access_key_id = s3_config.get("access_key_id", "")
            secret_access_key = s3_config.get("secret_access_key", "")
            region = s3_config.get("region", "us-east-1")

            if not bucket_name:
                raise APIException(
                    status_code=400,
                    code="MISSING_BUCKET_NAME",
                    message="S3 bucket name is required",
                )

            # Validate bucket name format (AWS S3 rules)
            # Bucket names must be 3-63 characters, lowercase, alphanumeric and hyphens only
            bucket_pattern = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")
            if (
                not bucket_pattern.match(bucket_name)
                or len(bucket_name) < 3
                or len(bucket_name) > 63
            ):
                raise APIException(
                    status_code=400,
                    code="INVALID_BUCKET_NAME",
                    message="Bucket name must be 3-63 characters, lowercase, alphanumeric and hyphens only",
                )

            # Validate AWS region
            if region not in AWS_VALID_REGIONS:
                raise APIException(
                    status_code=400,
                    code="INVALID_AWS_REGION",
                    message=f"Invalid AWS region: {region}. Must be one of: {', '.join(AWS_VALID_REGIONS[:10])}...",
                )

            if not access_key_id or not secret_access_key:
                raise APIException(
                    status_code=400,
                    code="MISSING_CREDENTIALS",
                    message="S3 access key ID and secret access key are required",
                )

            # Encrypt credentials before storing
            encrypted_secret = encrypt_credentials(secret_access_key, tenant_id)

            self.config_service.set(
                tenant_id=tenant_id,
                module=self.module,
                key="storage.s3.bucket_name",
                value=bucket_name,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.config_service.set(
                tenant_id=tenant_id,
                module=self.module,
                key="storage.s3.access_key_id",
                value=access_key_id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.config_service.set(
                tenant_id=tenant_id,
                module=self.module,
                key="storage.s3.secret_access_key",
                value=encrypted_secret,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.config_service.set(
                tenant_id=tenant_id,
                module=self.module,
                key="storage.s3.region",
                value=region,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        # Update local configuration if needed
        if backend in ("local", "hybrid"):
            local_config = config.get("local", {})
            base_path = local_config.get("base_path", "./storage")

            self.config_service.set(
                tenant_id=tenant_id,
                module=self.module,
                key="storage.local.base_path",
                value=base_path,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return self.get_storage_config(tenant_id)

    async def test_s3_connection(
        self, tenant_id: UUID, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Test S3 connection with provided credentials.

        Args:
            tenant_id: Tenant ID
            config: S3 configuration dictionary

        Returns:
            Dictionary with test results

        Raises:
            APIException: If connection test fails
        """
        bucket_name = config.get("bucket_name", "")
        access_key_id = config.get("access_key_id", "")
        secret_access_key = config.get("secret_access_key", "")
        region = config.get("region", "us-east-1")

        if not all([bucket_name, access_key_id, secret_access_key]):
            raise APIException(
                status_code=400,
                code="MISSING_CREDENTIALS",
                message="Bucket name, access key ID, and secret access key are required",
            )

        try:
            # Create temporary S3 backend to test connection
            s3_backend = S3StorageBackend(
                bucket_name=bucket_name,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region=region,
            )

            # Try to list bucket (simple connection test)
            client = s3_backend._get_client()
            client.head_bucket(Bucket=bucket_name)

            return {
                "success": True,
                "message": "S3 connection successful",
                "bucket_name": bucket_name,
                "region": region,
            }
        except Exception as e:
            logger.error(f"S3 connection test failed: {e}", exc_info=True)
            raise APIException(
                status_code=400,
                code="S3_CONNECTION_FAILED",
                message=f"S3 connection test failed: {str(e)}",
            )

    def get_storage_stats(self, tenant_id: UUID) -> dict[str, Any]:
        """Get storage statistics.

        Args:
            tenant_id: Tenant ID

        Returns:
            Dictionary with storage statistics
        """
        from sqlalchemy import distinct, func

        from app.models.file import File, FilePermission, FileVersion
        from app.models.folder import Folder, FolderPermission

        # Calculate total space used
        total_size = (
            self.db.query(func.sum(File.size))
            .filter(File.tenant_id == tenant_id, File.is_current)
            .scalar()
        ) or 0

        # Count total files
        total_files = (
            self.db.query(File)
            .filter(File.tenant_id == tenant_id, File.is_current)
            .count()
        )

        # Count files by MIME type
        mime_stats = (
            self.db.query(File.mime_type, func.count(File.id).label("count"))
            .filter(File.tenant_id == tenant_id, File.is_current)
            .group_by(File.mime_type)
            .all()
        )

        mime_distribution = {mime: count for mime, count in mime_stats}

        # Count files by entity type
        entity_stats = (
            self.db.query(File.entity_type, func.count(File.id).label("count"))
            .filter(File.tenant_id == tenant_id, File.is_current)
            .filter(File.entity_type.isnot(None))
            .group_by(File.entity_type)
            .all()
        )

        entity_distribution = {
            entity_type: count for entity_type, count in entity_stats
        }

        # Count total versions
        total_versions = (
            self.db.query(FileVersion)
            .filter(FileVersion.tenant_id == tenant_id)
            .count()
        )

        # Count total folders
        total_folders = (
            self.db.query(Folder).filter(Folder.tenant_id == tenant_id).count()
        )

        # Check if file_permissions table exists and get stats
        files_with_permissions = 0
        file_permission_distribution = {}
        try:
            # Check if table exists
            from sqlalchemy import inspect

            inspector = inspect(self.db.bind)
            if "file_permissions" in inspector.get_table_names():
                files_with_permissions = (
                    self.db.query(func.count(distinct(FilePermission.file_id)))
                    .filter(FilePermission.tenant_id == tenant_id)
                    .scalar()
                ) or 0

                file_permission_targets = (
                    self.db.query(
                        FilePermission.target_type,
                        func.count(FilePermission.id).label("count"),
                    )
                    .filter(FilePermission.tenant_id == tenant_id)
                    .group_by(FilePermission.target_type)
                    .all()
                )
                file_permission_distribution = {
                    target_type: count for target_type, count in file_permission_targets
                }
        except Exception:
            # Any error, default to 0/empty
            files_with_permissions = 0
            file_permission_distribution = {}

        # Check if folder_permissions table exists and get stats
        folders_with_permissions = 0
        folder_permission_distribution = {}
        try:
            from sqlalchemy import inspect

            inspector = inspect(self.db.bind)
            if "folder_permissions" in inspector.get_table_names():
                folders_with_permissions = (
                    self.db.query(func.count(distinct(FolderPermission.folder_id)))
                    .filter(FolderPermission.tenant_id == tenant_id)
                    .scalar()
                ) or 0

                folder_permission_targets = (
                    self.db.query(
                        FolderPermission.target_type,
                        func.count(FolderPermission.id).label("count"),
                    )
                    .filter(FolderPermission.tenant_id == tenant_id)
                    .group_by(FolderPermission.target_type)
                    .all()
                )
                folder_permission_distribution = {
                    target_type: count
                    for target_type, count in folder_permission_targets
                }
        except Exception:
            # Any error, default to 0/empty
            folders_with_permissions = 0
            folder_permission_distribution = {}

        # Ensure all values are of correct type (no None values)
        return {
            "total_space_used": int(total_size) if total_size is not None else 0,
            "total_files": int(total_files) if total_files is not None else 0,
            "total_versions": int(total_versions) if total_versions is not None else 0,
            "total_folders": int(total_folders) if total_folders is not None else 0,
            "mime_distribution": dict(mime_distribution) if mime_distribution else {},
            "entity_distribution": (
                dict(entity_distribution) if entity_distribution else {}
            ),
            "files_with_permissions": (
                int(files_with_permissions) if files_with_permissions is not None else 0
            ),
            "folders_with_permissions": (
                int(folders_with_permissions)
                if folders_with_permissions is not None
                else 0
            ),
            "file_permission_distribution": (
                dict(file_permission_distribution)
                if file_permission_distribution
                else {}
            ),
            "folder_permission_distribution": (
                dict(folder_permission_distribution)
                if folder_permission_distribution
                else {}
            ),
        }

    def get_file_limits(self, tenant_id: UUID) -> dict[str, Any]:
        """Get file limits configuration.

        Args:
            tenant_id: Tenant ID

        Returns:
            Dictionary with file limits
        """
        return {
            "max_file_size": self.config_service.get(
                tenant_id, self.module, "limits.max_file_size", 100 * 1024 * 1024
            ),  # 100MB default
            "allowed_mime_types": self.config_service.get(
                tenant_id, self.module, "limits.allowed_mime_types", []
            ),
            "blocked_mime_types": self.config_service.get(
                tenant_id, self.module, "limits.blocked_mime_types", []
            ),
            "max_versions_per_file": self.config_service.get(
                tenant_id, self.module, "limits.max_versions_per_file", 10
            ),
            "retention_days": self.config_service.get(
                tenant_id, self.module, "limits.retention_days", None
            ),
        }

    def update_file_limits(
        self,
        tenant_id: UUID,
        limits: dict[str, Any],
        user_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Update file limits configuration.

        Args:
            tenant_id: Tenant ID
            limits: Limits dictionary
            user_id: User ID making the change
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Updated limits dictionary

        Raises:
            APIException: If limits are invalid
        """
        max_file_size = limits.get("max_file_size")
        if max_file_size is not None:
            if not isinstance(max_file_size, int):
                raise APIException(
                    status_code=400,
                    code="INVALID_MAX_FILE_SIZE_TYPE",
                    message="Max file size must be an integer",
                )
            if max_file_size <= 0:
                raise APIException(
                    status_code=400,
                    code="INVALID_MAX_FILE_SIZE",
                    message="Max file size must be greater than 0",
                )
            self.config_service.set(
                tenant_id=tenant_id,
                module=self.module,
                key="limits.max_file_size",
                value=max_file_size,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        allowed_mime_types = limits.get("allowed_mime_types")
        if allowed_mime_types is not None:
            if not isinstance(allowed_mime_types, list):
                raise APIException(
                    status_code=400,
                    code="INVALID_ALLOWED_MIME_TYPES",
                    message="Allowed MIME types must be a list",
                )
            # Validate MIME type format
            for mime_type in allowed_mime_types:
                if not isinstance(mime_type, str) or not MIME_TYPE_PATTERN.match(
                    mime_type
                ):
                    raise APIException(
                        status_code=400,
                        code="INVALID_MIME_TYPE_FORMAT",
                        message=f"Invalid MIME type format: {mime_type}. Must be in format 'type/subtype' or 'type/*' or '*/*'",
                    )
            self.config_service.set(
                tenant_id=tenant_id,
                module=self.module,
                key="limits.allowed_mime_types",
                value=allowed_mime_types,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        blocked_mime_types = limits.get("blocked_mime_types")
        if blocked_mime_types is not None:
            if not isinstance(blocked_mime_types, list):
                raise APIException(
                    status_code=400,
                    code="INVALID_BLOCKED_MIME_TYPES",
                    message="Blocked MIME types must be a list",
                )
            # Validate MIME type format
            for mime_type in blocked_mime_types:
                if not isinstance(mime_type, str) or not MIME_TYPE_PATTERN.match(
                    mime_type
                ):
                    raise APIException(
                        status_code=400,
                        code="INVALID_MIME_TYPE_FORMAT",
                        message=f"Invalid MIME type format: {mime_type}. Must be in format 'type/subtype' or 'type/*' or '*/*'",
                    )
            self.config_service.set(
                tenant_id=tenant_id,
                module=self.module,
                key="limits.blocked_mime_types",
                value=blocked_mime_types,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        max_versions = limits.get("max_versions_per_file")
        if max_versions is not None:
            if max_versions < 1:
                raise APIException(
                    status_code=400,
                    code="INVALID_MAX_VERSIONS",
                    message="Max versions per file must be at least 1",
                )
            self.config_service.set(
                tenant_id=tenant_id,
                module=self.module,
                key="limits.max_versions_per_file",
                value=max_versions,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        retention_days = limits.get("retention_days")
        if retention_days is not None:
            if retention_days < 0:
                raise APIException(
                    status_code=400,
                    code="INVALID_RETENTION_DAYS",
                    message="Retention days must be non-negative",
                )
            self.config_service.set(
                tenant_id=tenant_id,
                module=self.module,
                key="limits.retention_days",
                value=retention_days,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return self.get_file_limits(tenant_id)

    def get_thumbnail_config(self, tenant_id: UUID) -> dict[str, Any]:
        """Get thumbnail configuration.

        Args:
            tenant_id: Tenant ID

        Returns:
            Dictionary with thumbnail configuration
        """
        return {
            "default_width": self.config_service.get(
                tenant_id, self.module, "thumbnails.default_width", 300
            ),
            "default_height": self.config_service.get(
                tenant_id, self.module, "thumbnails.default_height", 300
            ),
            "quality": self.config_service.get(
                tenant_id, self.module, "thumbnails.quality", 85
            ),
            "cache_enabled": self.config_service.get(
                tenant_id, self.module, "thumbnails.cache_enabled", True
            ),
            "max_cache_size": self.config_service.get(
                tenant_id, self.module, "thumbnails.max_cache_size", 1024 * 1024 * 1024
            ),  # 1GB default
        }

    def update_thumbnail_config(
        self,
        tenant_id: UUID,
        config: dict[str, Any],
        user_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Update thumbnail configuration.

        Args:
            tenant_id: Tenant ID
            config: Thumbnail configuration dictionary
            user_id: User ID making the change
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Updated thumbnail configuration dictionary

        Raises:
            APIException: If configuration is invalid
        """
        default_width = config.get("default_width")
        if default_width is not None:
            if default_width <= 0:
                raise APIException(
                    status_code=400,
                    code="INVALID_WIDTH",
                    message="Default width must be greater than 0",
                )
            self.config_service.set(
                tenant_id=tenant_id,
                module=self.module,
                key="thumbnails.default_width",
                value=default_width,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        default_height = config.get("default_height")
        if default_height is not None:
            if default_height <= 0:
                raise APIException(
                    status_code=400,
                    code="INVALID_HEIGHT",
                    message="Default height must be greater than 0",
                )
            self.config_service.set(
                tenant_id=tenant_id,
                module=self.module,
                key="thumbnails.default_height",
                value=default_height,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        quality = config.get("quality")
        if quality is not None:
            if not (1 <= quality <= 100):
                raise APIException(
                    status_code=400,
                    code="INVALID_QUALITY",
                    message="Quality must be between 1 and 100",
                )
            self.config_service.set(
                tenant_id=tenant_id,
                module=self.module,
                key="thumbnails.quality",
                value=quality,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        cache_enabled = config.get("cache_enabled")
        if cache_enabled is not None:
            self.config_service.set(
                tenant_id=tenant_id,
                module=self.module,
                key="thumbnails.cache_enabled",
                value=bool(cache_enabled),
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        max_cache_size = config.get("max_cache_size")
        if max_cache_size is not None:
            if max_cache_size < 0:
                raise APIException(
                    status_code=400,
                    code="INVALID_CACHE_SIZE",
                    message="Max cache size must be non-negative",
                )
            self.config_service.set(
                tenant_id=tenant_id,
                module=self.module,
                key="thumbnails.max_cache_size",
                value=max_cache_size,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return self.get_thumbnail_config(tenant_id)
