"""File repository for data access operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.file import File, FilePermission, FileVersion
from app.models.tag import EntityTag


class FileRepository:
    """Repository for file data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    # File operations
    def create(self, file_data: dict) -> File:
        """Create a new file."""
        import logging

        logger = logging.getLogger(__name__)

        try:
            logger.debug(f"Creating file record with data: {file_data}")
            file = File(**file_data)
            logger.debug(f"File object created: {file.id}")

            self.db.add(file)
            logger.debug(f"File added to session: {file.id}")

            # Flush to check for validation errors before commit
            self.db.flush()
            logger.debug(f"File flushed to DB: {file.id}")

            self.db.commit()
            logger.info(
                f"File committed successfully in DB: {file.id} (name: {file_data.get('name', 'unknown')})"
            )

            # Verificar inmediatamente después del commit que el archivo está en la BD
            try:
                # Hacer una consulta directa para verificar que el commit funcionó
                from sqlalchemy import text

                result = self.db.execute(
                    text("SELECT id FROM files WHERE id = :file_id"),
                    {"file_id": str(file.id)},
                ).fetchone()
                if result:
                    logger.info(
                        f"File verified in DB immediately after commit: {file.id}"
                    )
                else:
                    logger.error(
                        f"CRITICAL: File {file.id} was committed but not found in DB!"
                    )
            except Exception as verify_error:
                logger.warning(
                    f"Could not verify file in DB (non-critical): {verify_error}"
                )

            self.db.refresh(file)
            logger.debug(f"File refreshed from DB: {file.id}")

            return file
        except Exception as e:
            logger.error(f"Error creating file record: {e}", exc_info=True)
            logger.error(f"File data that failed: {file_data}")
            try:
                self.db.rollback()
                logger.debug("Rollback completed")
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
            raise

    def get_by_id(
        self, file_id: UUID, tenant_id: UUID, current_only: bool = True
    ) -> File | None:
        """Get file by ID and tenant."""
        from sqlalchemy.orm import joinedload

        query = (
            self.db.query(File)
            .options(joinedload(File.uploaded_by_user))
            .filter(File.id == file_id, File.tenant_id == tenant_id)
        )
        if current_only:
            query = query.filter(File.is_current, File.deleted_at.is_(None))
        return query.first()

    def get_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        current_only: bool = True,
    ) -> list[File]:
        """Get files by entity."""
        from sqlalchemy.orm import joinedload

        query = (
            self.db.query(File)
            .options(joinedload(File.uploaded_by_user))
            .filter(
                File.entity_type == entity_type,
                File.entity_id == entity_id,
                File.tenant_id == tenant_id,
            )
        )
        if current_only:
            query = query.filter(File.is_current, File.deleted_at.is_(None))
        return query.order_by(File.created_at.desc()).all()

    def count_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        current_only: bool = True,
    ) -> int:
        """Count files by entity."""
        from sqlalchemy import func

        query = self.db.query(func.count(File.id)).filter(
            File.entity_type == entity_type,
            File.entity_id == entity_id,
            File.tenant_id == tenant_id,
        )
        if current_only:
            query = query.filter(File.is_current)
        return query.scalar() or 0

    def get_all(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        current_only: bool = True,
        folder_id: UUID | None = None,
        tag_ids: list[UUID] | None = None,
    ) -> list[File]:
        """Get all files for a tenant.

        Args:
            tenant_id: Tenant ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            current_only: Only get current files (not deleted)
            folder_id: Filter by folder ID (None for root)
            tag_ids: Filter by tag IDs (files must have ALL specified tags)

        Returns:
            List of File objects
        """
        from sqlalchemy.orm import joinedload

        query = (
            self.db.query(File)
            .options(joinedload(File.uploaded_by_user))
            .filter(File.tenant_id == tenant_id)
        )
        if current_only:
            query = query.filter(File.is_current).filter(File.deleted_at.is_(None))
        # Only filter by folder_id if it's explicitly provided (not None)
        # If folder_id is None, we don't filter (get all files regardless of folder)
        if folder_id is not None:
            query = query.filter(File.folder_id == folder_id)

        # Filter by tags if provided
        if tag_ids:
            # Files must have ALL specified tags (AND logic)
            # Use subquery approach to avoid GROUP BY issues with joinedload
            from sqlalchemy import func

            # First, find file IDs that have all the specified tags
            subquery = (
                self.db.query(EntityTag.entity_id)
                .filter(
                    EntityTag.entity_type == "file",
                    EntityTag.tag_id.in_(tag_ids),
                    EntityTag.tenant_id == tenant_id,
                )
                .group_by(EntityTag.entity_id)
                .having(func.count(func.distinct(EntityTag.tag_id)) == len(tag_ids))
                .subquery()
            )

            # Filter the main query by file IDs from subquery
            query = query.filter(File.id.in_(self.db.query(subquery.c.entity_id)))

        return query.order_by(File.created_at.desc()).offset(skip).limit(limit).all()

    def count_all(
        self,
        tenant_id: UUID,
        current_only: bool = True,
        folder_id: UUID | None = None,
        tag_ids: list[UUID] | None = None,
    ) -> int:
        """Count all files for a tenant.

        Args:
            tenant_id: Tenant ID
            current_only: Only count current files (not deleted)
            folder_id: Filter by folder ID (None for root)
            tag_ids: Filter by tag IDs (files must have ALL specified tags)

        Returns:
            Count of files
        """
        from sqlalchemy import func

        query = self.db.query(func.count(File.id)).filter(File.tenant_id == tenant_id)
        if current_only:
            query = query.filter(File.is_current, File.deleted_at.is_(None))
        # Only filter by folder_id if it's explicitly provided (not None)
        # If folder_id is None, we don't filter (count all files regardless of folder)
        if folder_id is not None:
            query = query.filter(File.folder_id == folder_id)

        # Filter by tags if provided
        if tag_ids:
            # Files must have ALL specified tags (AND logic)
            from sqlalchemy import func

            # Use subquery to count distinct files with all tags
            subquery = (
                self.db.query(EntityTag.entity_id)
                .filter(
                    EntityTag.entity_type == "file",
                    EntityTag.tag_id.in_(tag_ids),
                    EntityTag.tenant_id == tenant_id,
                )
                .group_by(EntityTag.entity_id)
                .having(func.count(EntityTag.tag_id.distinct()) == len(tag_ids))
                .subquery()
            )
            query = query.filter(File.id.in_(self.db.query(subquery.c.entity_id)))
            # Count distinct files
            return query.scalar() or 0

        return query.scalar() or 0

    def update(self, file_id: UUID, tenant_id: UUID, file_data: dict) -> File | None:
        """Update a file."""
        file = self.get_by_id(file_id, tenant_id)
        if not file:
            return None
        for key, value in file_data.items():
            setattr(file, key, value)
        self.db.commit()
        self.db.refresh(file)
        return file

    def delete(self, file_id: UUID, tenant_id: UUID) -> bool:
        """Soft delete by setting is_current=False and deleted_at."""
        from datetime import UTC, datetime

        file = self.get_by_id(file_id, tenant_id)
        if not file:
            return False
        file.is_current = False
        file.deleted_at = datetime.now(UTC)
        self.db.commit()
        return True

    # FileVersion operations
    def create_version(self, version_data: dict) -> FileVersion:
        """Create a new file version."""
        version = FileVersion(**version_data)
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def get_versions(self, file_id: UUID, tenant_id: UUID) -> list[FileVersion]:
        """Get all versions of a file."""
        return (
            self.db.query(FileVersion)
            .filter(FileVersion.file_id == file_id, FileVersion.tenant_id == tenant_id)
            .order_by(FileVersion.version_number.desc())
            .all()
        )

    def get_version_by_id(
        self, version_id: UUID, tenant_id: UUID
    ) -> FileVersion | None:
        """Get a specific version by ID."""
        return (
            self.db.query(FileVersion)
            .filter(FileVersion.id == version_id, FileVersion.tenant_id == tenant_id)
            .first()
        )

    def get_latest_version_number(self, file_id: UUID) -> int:
        """Get the latest version number for a file."""
        latest = (
            self.db.query(FileVersion)
            .filter(FileVersion.file_id == file_id)
            .order_by(FileVersion.version_number.desc())
            .first()
        )
        if latest:
            return latest.version_number
        # Check current file version
        file = self.db.query(File).filter(File.id == file_id).first()
        return file.version_number if file else 0

    # FilePermission operations
    def create_permission(self, permission_data: dict) -> FilePermission:
        """Create a new file permission."""
        permission = FilePermission(**permission_data)
        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)
        return permission

    def get_permissions(self, file_id: UUID, tenant_id: UUID) -> list[FilePermission]:
        """Get all permissions for a file."""
        return (
            self.db.query(FilePermission)
            .filter(
                FilePermission.file_id == file_id, FilePermission.tenant_id == tenant_id
            )
            .all()
        )

    def update_permission(
        self, permission_id: UUID, tenant_id: UUID, permission_data: dict
    ) -> FilePermission | None:
        """Update a file permission."""
        permission = (
            self.db.query(FilePermission)
            .filter(
                FilePermission.id == permission_id,
                FilePermission.tenant_id == tenant_id,
            )
            .first()
        )
        if not permission:
            return None
        for key, value in permission_data.items():
            setattr(permission, key, value)
        self.db.commit()
        self.db.refresh(permission)
        return permission

    def delete_permission(self, permission_id: UUID, tenant_id: UUID) -> bool:
        """Delete a file permission."""
        permission = (
            self.db.query(FilePermission)
            .filter(
                FilePermission.id == permission_id,
                FilePermission.tenant_id == tenant_id,
            )
            .first()
        )
        if not permission:
            return False
        self.db.delete(permission)
        self.db.commit()
        return True

    def restore(self, file_id: UUID, tenant_id: UUID) -> bool:
        """Restore a soft-deleted file."""
        # Get file even if deleted (current_only=False)
        file = self.get_by_id(file_id, tenant_id, current_only=False)
        if not file:
            return False
        if file.deleted_at is None:
            return False  # Already restored or never deleted
        file.is_current = True
        file.deleted_at = None
        self.db.commit()
        return True

    def get_deleted_files_for_cleanup(
        self, tenant_id: UUID, retention_days: int
    ) -> list[File]:
        """Get files deleted more than retention_days ago."""
        from datetime import UTC, datetime, timedelta

        cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)
        return (
            self.db.query(File)
            .filter(
                File.tenant_id == tenant_id,
                File.deleted_at.isnot(None),
                File.deleted_at < cutoff_date,
            )
            .all()
        )
