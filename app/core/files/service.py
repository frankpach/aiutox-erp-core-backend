"""File service for file management."""

import io
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any
from uuid import UUID

from PIL import Image
from sqlalchemy.orm import Session

from app.core.files.storage import (
    HybridStorageBackend,
    LocalStorageBackend,
    S3StorageBackend,
)
from app.core.files.storage_config_service import StorageConfigService
from app.core.pubsub import EventPublisher, get_event_publisher
from app.core.pubsub.models import EventMetadata
from app.core.security.encryption import decrypt_credentials
from app.core.tags.service import TagService
from app.models.file import File, FilePermission, FileVersion, StorageBackend
from app.models.tag import Tag
from app.repositories.file_repository import FileRepository

logger = logging.getLogger(__name__)


class FileService:
    """Service for file management."""

    def __init__(
        self,
        db: Session,
        storage_backend=None,
        event_publisher: EventPublisher | None = None,
        tenant_id: UUID | None = None,
    ):
        """Initialize file service.

        Args:
            db: Database session
            storage_backend: Storage backend instance (created if not provided)
            event_publisher: EventPublisher instance (created if not provided)
            tenant_id: Tenant ID for reading storage configuration (required if storage_backend is None)
        """
        self.db = db
        self.repository = FileRepository(db)
        self.event_publisher = event_publisher or get_event_publisher()
        self._storage_config_service = StorageConfigService(db)
        self._tag_service = TagService(db)

        # Initialize storage backend
        if storage_backend is None:
            if tenant_id is None:
                # Fallback to environment variable for backward compatibility
                logger.warning(
                    "FileService initialized without tenant_id. Using environment variable for storage backend."
                )
                use_s3 = os.getenv("USE_S3_STORAGE", "false").lower() == "true"
                self.storage_backend = HybridStorageBackend(use_s3=use_s3)
            else:
                # Read configuration from ConfigService
                self.storage_backend = self._get_storage_backend_from_config(tenant_id)
        else:
            self.storage_backend = storage_backend

    def _get_storage_backend_from_config(self, tenant_id: UUID):
        """Get storage backend from configuration.

        Args:
            tenant_id: Tenant ID

        Returns:
            Storage backend instance
        """
        try:
            config = self._storage_config_service.get_storage_config(tenant_id)
            backend_type = config.get("backend", "local")

            if backend_type == "local":
                local_config = config.get("local", {})
                base_path = local_config.get("base_path", "./storage")
                return LocalStorageBackend(base_path=base_path)

            elif backend_type == "s3":
                s3_config = config.get("s3", {})
                bucket_name = s3_config.get("bucket_name", "")
                access_key_id = s3_config.get("access_key_id", "")
                # Get encrypted secret from config service
                encrypted_secret = self._storage_config_service.config_service.get(
                    tenant_id, "files", "storage.s3.secret_access_key", ""
                )
                region = s3_config.get("region", "us-east-1")

                if not bucket_name or not access_key_id or not encrypted_secret:
                    logger.warning(
                        f"Incomplete S3 configuration for tenant {tenant_id}. Falling back to local storage."
                    )
                    return LocalStorageBackend()

                # Decrypt credentials
                try:
                    secret_access_key = decrypt_credentials(encrypted_secret, tenant_id)
                except Exception as e:
                    logger.error(f"Failed to decrypt S3 credentials for tenant {tenant_id}: {e}")
                    return LocalStorageBackend()

                return S3StorageBackend(
                    bucket_name=bucket_name,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    region=region,
                )

            elif backend_type == "hybrid":
                # For hybrid mode, we'll use S3 as primary if configured, otherwise local
                # This is a simplified implementation - a full hybrid would need routing logic
                local_config = config.get("local", {})
                base_path = local_config.get("base_path", "./storage")
                local_backend = LocalStorageBackend(base_path=base_path)

                s3_config = config.get("s3", {})
                bucket_name = s3_config.get("bucket_name", "")
                access_key_id = s3_config.get("access_key_id", "")
                # Get encrypted secret from config service
                encrypted_secret = self._storage_config_service.config_service.get(
                    tenant_id, "files", "storage.s3.secret_access_key", ""
                )
                region = s3_config.get("region", "us-east-1")

                if not bucket_name or not access_key_id or not encrypted_secret:
                    logger.warning(
                        f"Incomplete S3 configuration for hybrid backend for tenant {tenant_id}. Using local only."
                    )
                    return local_backend

                # Decrypt credentials
                try:
                    secret_access_key = decrypt_credentials(encrypted_secret, tenant_id)
                except Exception as e:
                    logger.error(f"Failed to decrypt S3 credentials for tenant {tenant_id}: {e}")
                    return local_backend

                # For hybrid mode, prefer S3 but fallback to local if S3 fails
                # Create HybridStorageBackend with use_s3=True to use S3 as primary
                # Note: This is a simplified implementation
                # A full hybrid implementation would need routing logic based on file size, type, etc.
                return HybridStorageBackend(use_s3=True, bucket_name=bucket_name, aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, region=region)

            else:
                logger.warning(f"Unknown backend type: {backend_type}. Falling back to local storage.")
                return LocalStorageBackend()

        except Exception as e:
            logger.error(f"Error reading storage configuration for tenant {tenant_id}: {e}", exc_info=True)
            # Fallback to local storage
            return LocalStorageBackend()

    def reload_storage_backend(self, tenant_id: UUID):
        """Reload storage backend from configuration.

        This method allows dynamic backend changes. Use with caution and validate
        that existing files are accessible with the new backend.

        Args:
            tenant_id: Tenant ID

        Returns:
            True if backend was reloaded successfully, False otherwise
        """
        try:
            new_backend = self._get_storage_backend_from_config(tenant_id)
            self.storage_backend = new_backend
            logger.info(f"Storage backend reloaded for tenant {tenant_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to reload storage backend for tenant {tenant_id}: {e}", exc_info=True)
            return False

    def _generate_storage_path(
        self, tenant_id: UUID, entity_type: str | None, filename: str
    ) -> str:
        """Generate storage path for a file.

        Args:
            tenant_id: Tenant ID
            entity_type: Entity type (optional)
            filename: Original filename

        Returns:
            Storage path
        """
        # Generate path: tenant_id/entity_type/year/month/filename
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        path_parts = [str(tenant_id)]
        if entity_type:
            path_parts.append(entity_type)
        path_parts.extend([str(now.year), f"{now.month:02d}", filename])
        return "/".join(path_parts)

    def _get_file_extension(self, filename: str) -> str:
        """Get file extension from filename."""
        return Path(filename).suffix.lower()

    def _detect_mime_type(self, filename: str, content: bytes | None = None) -> str:
        """Detect MIME type from filename or content."""
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            return mime_type
        # Fallback to application/octet-stream
        return "application/octet-stream"

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        entity_type: str | None,
        entity_id: UUID | None,
        tenant_id: UUID,
        user_id: UUID,
        description: str | None = None,
        metadata: dict | None = None,
        folder_id: UUID | None = None,
        permissions: list[dict] | None = None,
    ) -> File:
        """Upload a file.

        Args:
            file_content: File content as bytes
            filename: Original filename
            entity_type: Entity type (e.g., 'product', 'order')
            entity_id: Entity ID
            tenant_id: Tenant ID
            user_id: User ID who uploaded the file
            description: File description (optional)
            metadata: Additional metadata (optional)

        Returns:
            Created File object
        """
        # Generate storage path
        storage_path = self._generate_storage_path(tenant_id, entity_type, filename)

        # Upload to storage
        await self.storage_backend.upload(file_content, storage_path)

        # Get file info
        file_size = len(file_content)
        file_extension = self._get_file_extension(filename)
        mime_type = self._detect_mime_type(filename, file_content)

        # Determine storage backend type
        backend = self.storage_backend
        if isinstance(backend, HybridStorageBackend):
            # HybridStorageBackend has a .backend attribute
            backend = backend.backend

        if isinstance(backend, S3StorageBackend):
            storage_backend_type = StorageBackend.S3.value  # Use .value to get string
        else:
            storage_backend_type = StorageBackend.LOCAL.value  # Use .value to get string

        logger.debug(f"Storage backend type: {storage_backend_type}, storage_path: {storage_path}")

        # Get storage URL
        storage_url = await self.storage_backend.get_url(storage_path)

        # Create file record
        file_data = {
            "tenant_id": tenant_id,
            "name": filename,
            "original_name": filename,
            "mime_type": mime_type,
            "size": file_size,
            "extension": file_extension,
            "storage_backend": storage_backend_type,
            "storage_path": storage_path,
            "storage_url": storage_url,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "folder_id": folder_id,
            "description": description,
            "metadata": metadata,
            "version_number": 1,
            "is_current": True,
            "uploaded_by": user_id,
        }
        logger.info(f"Attempting to create file record in DB with data: tenant_id={tenant_id}, filename={filename}, size={file_size}")

        try:
            file = self.repository.create(file_data)
            logger.info(f"File record created successfully in DB: {file.id} ({filename})")

            # Verify the file was actually saved
            verify_file = self.repository.get_by_id(file.id, tenant_id)
            if verify_file:
                logger.info(f"File verified in DB: {verify_file.id}")
            else:
                logger.error(f"File was created but cannot be retrieved: {file.id}")
        except Exception as e:
            logger.error(f"Failed to create file record in DB: {e}", exc_info=True)
            logger.error(f"File data that failed: {file_data}")
            # Try to clean up uploaded file from storage
            try:
                await self.storage_backend.delete(storage_path)
                logger.info(f"Cleaned up storage file: {storage_path}")
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup storage file: {cleanup_error}")
            raise

        # IMPORTANTE: Asegurar que el commit se mantenga antes de continuar
        # Hacer un flush explícito para asegurar que los cambios están en la sesión
        try:
            self.db.flush()
            logger.debug(f"Session flushed after file creation: {file.id}")
        except Exception as e:
            logger.warning(f"Flush after file creation failed (non-critical): {e}")

        # Publish event (non-blocking - don't fail if event fails)
        try:
            await self.event_publisher.publish(
                event_type="file.uploaded",
                entity_type="file",
                entity_id=file.id,
                tenant_id=tenant_id,
                user_id=user_id,
                metadata=EventMetadata(
                    source="file_service",
                    version="1.0",
                    additional_data={
                        "filename": filename,
                        "entity_type": entity_type,
                        "entity_id": str(entity_id) if entity_id else None,
                        "size": file_size,
                    },
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to publish file.uploaded event: {e}", exc_info=True)
            # Don't fail the upload if event publishing fails

        # Create initial version (v1) - IMPORTANT: Every file must have at least one version
        try:
            self.repository.create_version(
                {
                    "file_id": file.id,
                    "tenant_id": tenant_id,
                    "version_number": 1,
                    "storage_path": storage_path,
                    "storage_backend": storage_backend_type,
                    "size": file_size,
                    "mime_type": mime_type,
                    "change_description": "Initial version",
                    "created_by": user_id,
                }
            )
            logger.info(f"Initial version (v1) created for file: {file.id}")
        except Exception as e:
            logger.error(f"Failed to create initial version for file {file.id}: {e}", exc_info=True)
            # This is critical - if version creation fails, we should rollback or at least log it
            # However, the file is already created, so we continue but log the error

        # Set permissions if provided (non-blocking - don't fail if permissions fail)
        if permissions:
            try:
                self.set_file_permissions(file.id, permissions, tenant_id)
                logger.info(f"Permissions set for file: {file.id}")
            except Exception as e:
                logger.warning(f"Failed to set file permissions: {e}", exc_info=True)
                # Don't fail the upload if permissions fail - file is already created

        # Verificación final: asegurar que el archivo todavía está en la BD
        try:
            final_check = self.repository.get_by_id(file.id, tenant_id)
            if not final_check:
                logger.error(f"CRITICAL: File {file.id} was created but is not in DB after all operations!")
            else:
                logger.info(f"Final verification: File {file.id} confirmed in DB")
        except Exception as e:
            logger.warning(f"Final verification failed (non-critical): {e}")

        logger.info(f"File uploaded successfully: {file.id} ({filename})")
        return file

    async def download_file(self, file_id: UUID, tenant_id: UUID) -> tuple[bytes, File]:
        """Download a file.

        Args:
            file_id: File ID
            tenant_id: Tenant ID

        Returns:
            Tuple of (file content, File object)

        Raises:
            FileNotFoundError: If file not found
        """
        file = self.repository.get_by_id(file_id, tenant_id)
        if not file or not file.is_current:
            raise FileNotFoundError(f"File {file_id} not found")

        # Download from storage
        content = await self.storage_backend.download(file.storage_path)

        return content, file

    async def delete_file(
        self, file_id: UUID, tenant_id: UUID, user_id: UUID
    ) -> bool:
        """Delete a file (soft delete).

        Args:
            file_id: File ID
            tenant_id: Tenant ID
            user_id: User ID who deleted the file

        Returns:
            True if deleted successfully
        """
        file = self.repository.get_by_id(file_id, tenant_id)
        if not file:
            return False

        # Soft delete (set is_current=False)
        deleted = self.repository.delete(file_id, tenant_id)

        if deleted:
            # Publish event
            try:
                await self.event_publisher.publish(
                    event_type="file.deleted",
                    entity_type="file",
                    entity_id=file_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    metadata=EventMetadata(
                        source="file_service",
                        version="1.0",
                        additional_data={"filename": file.name},
                    ),
                )
            except Exception as e:
                logger.warning(f"Failed to publish file.deleted event: {e}", exc_info=True)

            logger.info(f"File deleted: {file_id}")

        return deleted

    def get_file_versions(self, file_id: UUID, tenant_id: UUID) -> list[FileVersion]:
        """Get all versions of a file.

        Args:
            file_id: File ID
            tenant_id: Tenant ID

        Returns:
            List of FileVersion objects
        """
        return self.repository.get_versions(file_id, tenant_id)

    async def create_file_version(
        self,
        file_id: UUID,
        file_content: bytes,
        filename: str,
        tenant_id: UUID,
        user_id: UUID,
        change_description: str | None = None,
    ) -> FileVersion:
        """Create a new version of a file.

        Args:
            file_id: Original file ID
            file_content: New file content
            filename: New filename
            tenant_id: Tenant ID
            user_id: User ID who created the version
            change_description: Description of changes (optional)

        Returns:
            Created FileVersion object
        """
        # Get original file
        original_file = self.repository.get_by_id(file_id, tenant_id)
        if not original_file:
            raise FileNotFoundError(f"File {file_id} not found")

        # Get next version number
        next_version = self.repository.get_latest_version_number(file_id) + 1

        # Generate storage path for new version
        storage_path = self._generate_storage_path(
            tenant_id, original_file.entity_type, f"v{next_version}_{filename}"
        )

        # Upload new version to storage
        await self.storage_backend.upload(file_content, storage_path)

        # Get file info
        file_size = len(file_content)
        mime_type = self._detect_mime_type(filename, file_content)

        # Create version record
        version = self.repository.create_version(
            {
                "file_id": file_id,
                "tenant_id": tenant_id,
                "version_number": next_version,
                "storage_path": storage_path,
                "storage_backend": original_file.storage_backend,
                "size": file_size,
                "mime_type": mime_type,
                "change_description": change_description,
                "created_by": user_id,
            }
        )

        # Update original file version number
        original_file.version_number = next_version
        self.db.commit()

        logger.info(f"File version created: {file_id} v{next_version}")
        return version

    def set_file_permissions(
        self,
        file_id: UUID,
        permissions: list[dict],
        tenant_id: UUID,
    ) -> list[FilePermission]:
        """Set permissions for a file.

        Args:
            file_id: File ID
            permissions: List of permission dicts with target_type, target_id, and permission flags
            tenant_id: Tenant ID

        Returns:
            List of created FilePermission objects
        """
        # Delete existing permissions
        existing = self.repository.get_permissions(file_id, tenant_id)
        for perm in existing:
            self.repository.delete_permission(perm.id, tenant_id)

        # Create new permissions
        created_permissions = []
        for perm_data in permissions:
            perm = self.repository.create_permission(
                {
                    "file_id": file_id,
                    "tenant_id": tenant_id,
                    "target_type": perm_data["target_type"],
                    "target_id": perm_data["target_id"],
                    "can_view": perm_data.get("can_view", True),
                    "can_download": perm_data.get("can_download", True),
                    "can_edit": perm_data.get("can_edit", False),
                    "can_delete": perm_data.get("can_delete", False),
                }
            )
            created_permissions.append(perm)

        return created_permissions

    async def generate_thumbnail(
        self,
        file_id: UUID,
        tenant_id: UUID,
        width: int,
        height: int,
        quality: int = 80,
    ) -> bytes:
        """Generate thumbnail for an image file.

        Args:
            file_id: File ID
            tenant_id: Tenant ID
            width: Thumbnail width in pixels
            height: Thumbnail height in pixels
            quality: JPEG quality (1-100, default: 80)

        Returns:
            Thumbnail image as bytes (JPEG format)

        Raises:
            FileNotFoundError: If file not found
            ValueError: If file is not an image
        """
        # Get file record
        file = self.repository.get_by_id(file_id, tenant_id)
        if not file or not file.is_current:
            raise FileNotFoundError(f"File {file_id} not found")

        # Verify it's an image
        if not file.mime_type.startswith("image/"):
            raise ValueError(f"File {file_id} is not an image (mime_type: {file.mime_type})")

        # Download original file
        original_content = await self.storage_backend.download(file.storage_path)

        # Process image with PIL
        img = Image.open(io.BytesIO(original_content))

        # Create thumbnail maintaining aspect ratio
        img.thumbnail((width, height), Image.Resampling.LANCZOS)

        # Convert to JPEG
        output = io.BytesIO()

        # Handle transparency (RGBA, LA, P modes)
        if img.mode in ("RGBA", "LA", "P"):
            # Convert PNG with transparency to RGB
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
            elif img.mode == "LA":
                background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
            else:  # P mode (palette)
                if "transparency" in img.info:
                    # Convert palette with transparency
                    img = img.convert("RGBA")
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
            img = background

        # Save as JPEG
        img.save(output, format="JPEG", quality=quality, optimize=True)
        return output.getvalue()

    def count_files_by_entity(
        self, entity_type: str, entity_id: UUID, tenant_id: UUID, current_only: bool = True
    ) -> int:
        """Count files by entity.

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            tenant_id: Tenant ID
            current_only: Only count current files (default: True)

        Returns:
            Count of files
        """
        return self.repository.count_by_entity(entity_type, entity_id, tenant_id, current_only)

    def count_all_files(
        self, tenant_id: UUID, current_only: bool = True
    ) -> int:
        """Count all files for a tenant.

        Args:
            tenant_id: Tenant ID
            current_only: Only count current files (default: True)

        Returns:
            Count of files
        """
        return self.repository.count_all(tenant_id, current_only)

    def count_files_by_entity_user_can_view(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
    ) -> int:
        """Count files by entity that a user can view based on permissions.

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            tenant_id: Tenant ID
            user_id: User ID

        Returns:
            Count of files the user can view for the entity
        """
        # Get all files for the entity
        all_files = self.repository.get_by_entity(entity_type, entity_id, tenant_id)

        # Count files by permissions
        count = 0
        for file in all_files:
            try:
                if self.check_permissions(file.id, user_id, tenant_id, "view"):
                    count += 1
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.warning(f"Error checking permissions for file {file.id} in count: {e}")
                continue

        return count

    def check_permissions(
        self,
        file_id: UUID,
        user_id: UUID,
        tenant_id: UUID,
        permission: str,
    ) -> bool:
        """Check if a user has a specific permission on a file.

        Security:
        - File owner always has full access
        - Checks user-specific permissions first
        - Then checks role-based permissions
        - Then checks organization-based permissions
        - Multi-tenant isolation enforced

        Args:
            file_id: File ID
            user_id: User ID to check permissions for
            tenant_id: Tenant ID (for multi-tenancy)
            permission: Permission to check ("view", "download", "edit", "delete")

        Returns:
            True if user has permission, False otherwise

        Raises:
            FileNotFoundError: If file not found
        """
        logger.debug(
            f"Checking permission '{permission}' for file {file_id}, user {user_id}, tenant {tenant_id}"
        )

        try:
            # Get file (allow deleted files for permission check, but verify they're current)
            file = self.repository.get_by_id(file_id, tenant_id, current_only=False)
            if not file:
                logger.warning(
                    f"File {file_id} not found for tenant {tenant_id} when checking permissions"
                )
                raise FileNotFoundError(f"File {file_id} not found")

            # Check if file is current and not deleted
            if not file.is_current or file.deleted_at is not None:
                logger.debug(
                    f"File {file_id} is not current (is_current={file.is_current}, "
                    f"deleted_at={file.deleted_at})"
                )
                raise FileNotFoundError(f"File {file_id} not found or deleted")

            logger.debug(
                f"File {file_id} found: name={file.name}, uploaded_by={file.uploaded_by}, "
                f"is_current={file.is_current}, deleted_at={file.deleted_at}"
            )
        except FileNotFoundError:
            # Re-raise FileNotFoundError as-is
            raise
        except Exception as e:
            logger.error(
                f"Error retrieving file {file_id} for permission check: {e}",
                exc_info=True,
            )
            raise FileNotFoundError(f"File {file_id} not found") from e

        # File owner always has full access
        if file.uploaded_by == user_id:
            logger.debug(
                f"User {user_id} is owner of file {file_id}, granting full access for '{permission}'"
            )
            return True

        # Get all permissions for the file
        try:
            permissions = self.repository.get_permissions(file_id, tenant_id)
            logger.debug(
                f"Found {len(permissions)} permissions for file {file_id}"
            )
        except Exception as e:
            logger.error(
                f"Error retrieving permissions for file {file_id}: {e}",
                exc_info=True,
            )
            # If we can't get permissions, deny access (fail secure)
            return False

        # Map permission string to attribute
        permission_map = {
            "view": "can_view",
            "download": "can_download",
            "edit": "can_edit",
            "delete": "can_delete",
        }

        if permission not in permission_map:
            raise ValueError(f"Invalid permission: {permission}")

        permission_attr = permission_map[permission]

        # Check user-specific permissions
        for perm in permissions:
            if perm.target_type == "user" and perm.target_id == user_id:
                has_permission = getattr(perm, permission_attr, False)
                logger.debug(
                    f"User-specific permission found for file {file_id}, user {user_id}: "
                    f"{permission_attr}={has_permission}"
                )
                return has_permission

        # Check role-based permissions
        # Note: In this system, UserRole.role is a string (e.g., "admin", "viewer")
        # but FilePermission.target_id is a UUID. For role-based permissions to work,
        # we would need a mapping between role names and UUIDs, or store role names in FilePermission.
        # For now, we'll check if there's a direct UUID match (if roles were stored as UUIDs)
        from app.models.user_role import UserRole

        user_roles = (
            self.db.query(UserRole)
            .filter(UserRole.user_id == user_id)
            .all()
        )

        # Check if any permission matches a role UUID
        # This assumes role permissions use UUIDs that match some identifier
        # In practice, this would need a role-to-UUID mapping
        for perm in permissions:
            if perm.target_type == "role":
                # Try to match role UUID - this is a simplified check
                # In a real implementation, you'd need a mapping table
                # For now, we'll check if the permission exists and user has any role
                if user_roles and getattr(perm, permission_attr, False):
                    # This is a simplified check - in production you'd want proper role mapping
                    return True

        # Check organization-based permissions (if user belongs to organization)
        try:
            from app.models.user import User
            user = self.db.query(User).filter(User.id == user_id).first()
            if user and user.organization_id:
                logger.debug(
                    f"Checking organization permissions for user {user_id}, "
                    f"organization {user.organization_id}"
                )
                for perm in permissions:
                    if (
                        perm.target_type == "organization"
                        and perm.target_id == user.organization_id
                    ):
                        has_permission = getattr(perm, permission_attr, False)
                        if has_permission:
                            logger.debug(
                                f"Organization permission found for file {file_id}, "
                                f"organization {user.organization_id}: {permission_attr}={has_permission}"
                            )
                            return True
        except Exception as e:
            logger.warning(
                f"Error checking organization permissions for user {user_id}: {e}",
                exc_info=True,
            )

        # No permission found
        logger.debug(
            f"No permission found for file {file_id}, user {user_id}, permission '{permission}'"
        )
        return False

    def get_files_user_can_view(
        self,
        tenant_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        folder_id: UUID | None = None,
        tag_ids: list[UUID] | None = None,
    ) -> list[File]:
        """Get files that a user can view based on permissions.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            folder_id: Optional folder ID filter

        Returns:
            List of File objects the user can view
        """
        # Get all files for the tenant
        all_files = self.repository.get_all(
            tenant_id=tenant_id,
            skip=skip,
            limit=limit * 2,  # Get more files to account for filtering
            folder_id=folder_id,
            tag_ids=tag_ids,
        )

        # Filter files by permissions
        viewable_files = []
        for file in all_files:
            try:
                if self.check_permissions(file.id, user_id, tenant_id, "view"):
                    viewable_files.append(file)
                    if len(viewable_files) >= limit:
                        break
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.warning(f"Error checking permissions for file {file.id}: {e}")
                continue

        return viewable_files[:limit]

    def count_files_user_can_view(
        self,
        tenant_id: UUID,
        user_id: UUID,
        folder_id: UUID | None = None,
        tag_ids: list[UUID] | None = None,
    ) -> int:
        """Count files that a user can view based on permissions.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            folder_id: Optional folder ID filter

        Returns:
            Count of files the user can view
        """
        # Count files directly with tag filter if provided
        if tag_ids:
            return self.repository.count_all(
                tenant_id=tenant_id,
                current_only=True,
                folder_id=folder_id,
                tag_ids=tag_ids,
            )

        # Get all files for the tenant (without pagination for counting)
        all_files = self.repository.get_all(
            tenant_id=tenant_id,
            skip=0,
            limit=10000,  # Large limit to get all files for counting
            folder_id=folder_id,
            tag_ids=None,
        )

        # Count files by permissions
        count = 0
        for file in all_files:
            try:
                if self.check_permissions(file.id, user_id, tenant_id, "view"):
                    count += 1
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.warning(f"Error checking permissions for file {file.id} in count: {e}")
                continue

        return count

    async def cleanup_deleted_files(
        self, tenant_id: UUID, retention_days: int | None = None
    ) -> dict[str, Any]:
        """Clean up deleted files after retention period.

        Args:
            tenant_id: Tenant ID
            retention_days: Retention period in days (defaults to config)

        Returns:
            Dict with cleanup statistics
        """

        # Get retention_days from config if not provided
        if retention_days is None:
            limits = self._storage_config_service.get_file_limits(tenant_id)
            retention_days = limits.get("retention_days", 30)  # Default 30 days

        # Get files to cleanup
        files_to_cleanup = self.repository.get_deleted_files_for_cleanup(
            tenant_id, retention_days
        )

        files_deleted = 0
        storage_freed = 0
        errors = []

        for file in files_to_cleanup:
            try:
                # Delete physical file from storage
                await self.storage_backend.delete(file.storage_path)

                # Delete all versions
                versions = self.repository.get_versions(file.id, tenant_id)
                for version in versions:
                    try:
                        await self.storage_backend.delete(version.storage_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete version {version.id}: {e}")

                # Hard delete from database (CASCADE will handle related records)
                self.db.delete(file)
                self.db.commit()

                files_deleted += 1
                storage_freed += file.size

                # Publish event
                try:
                    await self.event_publisher.publish(
                        event_type="file.permanently_deleted",
                        entity_type="file",
                        entity_id=file.id,
                        tenant_id=tenant_id,
                        metadata=EventMetadata(
                            source="file_service",
                            version="1.0",
                            additional_data={
                                "filename": file.name,
                                "retention_days": retention_days,
                            },
                        ),
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to publish file.permanently_deleted event for {file.id}: {e}",
                        exc_info=True,
                    )
            except Exception as e:
                logger.error(f"Failed to cleanup file {file.id}: {e}", exc_info=True)
                errors.append({"file_id": str(file.id), "error": str(e)})
                self.db.rollback()

        return {
            "files_count": files_deleted,
            "storage_freed": storage_freed,
            "errors": errors,
        }

    async def restore_file(
        self, file_id: UUID, tenant_id: UUID, user_id: UUID
    ) -> bool:
        """Restore a soft-deleted file.

        Args:
            file_id: File ID
            tenant_id: Tenant ID
            user_id: User ID who restored the file

        Returns:
            True if restored successfully
        """
        restored = self.repository.restore(file_id, tenant_id)

        if restored:
            # Publish event
            try:
                await self.event_publisher.publish(
                    event_type="file.restored",
                    entity_type="file",
                    entity_id=file_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    metadata=EventMetadata(
                        source="file_service",
                        version="1.0",
                    ),
                )
            except Exception as e:
                logger.warning(f"Failed to publish file.restored event: {e}", exc_info=True)
            logger.info(f"File restored: {file_id}")

        return restored

    # Tag management methods
    def add_tags_to_file(
        self, file_id: UUID, tag_ids: list[UUID], tenant_id: UUID
    ) -> list[Tag]:
        """Add tags to a file.

        Args:
            file_id: File ID
            tag_ids: List of tag IDs to add
            tenant_id: Tenant ID

        Returns:
            List of Tag objects that were added

        Raises:
            FileNotFoundError: If file not found
            ValueError: If tag not found or already added
        """
        # Verify file exists
        file = self.repository.get_by_id(file_id, tenant_id)
        if not file or not file.is_current:
            raise FileNotFoundError(f"File {file_id} not found")

        added_tags = []
        for tag_id in tag_ids:
            try:
                self._tag_service.add_tag_to_entity(
                    tag_id=tag_id,
                    entity_type="file",
                    entity_id=file_id,
                    tenant_id=tenant_id,
                )
                # Get the tag to return it
                tag = self._tag_service.get_tag(tag_id, tenant_id)
                if tag:
                    added_tags.append(tag)
            except ValueError as e:
                logger.warning(
                    f"Failed to add tag {tag_id} to file {file_id}: {e}"
                )
                # Continue with other tags instead of failing completely
                continue

        logger.info(
            f"Added {len(added_tags)} tags to file {file_id}: {[t.id for t in added_tags]}"
        )
        return added_tags

    def remove_tag_from_file(
        self, file_id: UUID, tag_id: UUID, tenant_id: UUID
    ) -> bool:
        """Remove a tag from a file.

        Args:
            file_id: File ID
            tag_id: Tag ID to remove
            tenant_id: Tenant ID

        Returns:
            True if removed successfully

        Raises:
            FileNotFoundError: If file not found
        """
        # Verify file exists
        file = self.repository.get_by_id(file_id, tenant_id)
        if not file or not file.is_current:
            raise FileNotFoundError(f"File {file_id} not found")

        removed = self._tag_service.remove_tag_from_entity(
            tag_id=tag_id,
            entity_type="file",
            entity_id=file_id,
            tenant_id=tenant_id,
        )

        if removed:
            logger.info(f"Removed tag {tag_id} from file {file_id}")

        return removed

    def get_file_tags(self, file_id: UUID, tenant_id: UUID) -> list[Tag]:
        """Get all tags for a file.

        Args:
            file_id: File ID
            tenant_id: Tenant ID

        Returns:
            List of Tag objects

        Raises:
            FileNotFoundError: If file not found
        """
        # Verify file exists
        file = self.repository.get_by_id(file_id, tenant_id)
        if not file or not file.is_current:
            raise FileNotFoundError(f"File {file_id} not found")

        return self._tag_service.get_entity_tags(
            entity_type="file", entity_id=file_id, tenant_id=tenant_id
        )
