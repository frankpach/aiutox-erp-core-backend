"""File repository for data access operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.file import File, FilePermission, FileVersion


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
            logger.info(f"File committed successfully in DB: {file.id} (name: {file_data.get('name', 'unknown')})")

            # Verificar inmediatamente después del commit que el archivo está en la BD
            try:
                # Hacer una consulta directa para verificar que el commit funcionó
                from sqlalchemy import text
                result = self.db.execute(
                    text("SELECT id FROM files WHERE id = :file_id"),
                    {"file_id": str(file.id)}
                ).fetchone()
                if result:
                    logger.info(f"File verified in DB immediately after commit: {file.id}")
                else:
                    logger.error(f"CRITICAL: File {file.id} was committed but not found in DB!")
            except Exception as verify_error:
                logger.warning(f"Could not verify file in DB (non-critical): {verify_error}")

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

    def get_by_id(self, file_id: UUID, tenant_id: UUID) -> File | None:
        """Get file by ID and tenant."""
        from sqlalchemy.orm import joinedload
        return (
            self.db.query(File)
            .options(joinedload(File.uploaded_by_user))
            .filter(File.id == file_id, File.tenant_id == tenant_id)
            .first()
        )

    def get_by_entity(
        self, entity_type: str, entity_id: UUID, tenant_id: UUID, current_only: bool = True
    ) -> list[File]:
        """Get files by entity."""
        from sqlalchemy.orm import joinedload
        query = self.db.query(File).options(joinedload(File.uploaded_by_user)).filter(
            File.entity_type == entity_type,
            File.entity_id == entity_id,
            File.tenant_id == tenant_id,
        )
        if current_only:
            query = query.filter(File.is_current == True)
        return query.order_by(File.created_at.desc()).all()

    def count_by_entity(
        self, entity_type: str, entity_id: UUID, tenant_id: UUID, current_only: bool = True
    ) -> int:
        """Count files by entity."""
        from sqlalchemy import func

        query = self.db.query(func.count(File.id)).filter(
            File.entity_type == entity_type,
            File.entity_id == entity_id,
            File.tenant_id == tenant_id,
        )
        if current_only:
            query = query.filter(File.is_current == True)
        return query.scalar() or 0

    def get_all(
        self, tenant_id: UUID, skip: int = 0, limit: int = 100, current_only: bool = True, folder_id: UUID | None = None
    ) -> list[File]:
        """Get all files for a tenant."""
        from sqlalchemy.orm import joinedload
        query = self.db.query(File).options(joinedload(File.uploaded_by_user)).filter(File.tenant_id == tenant_id)
        if current_only:
            query = query.filter(File.is_current == True)
        if folder_id is not None:
            query = query.filter(File.folder_id == folder_id)
        elif folder_id is None:
            # If folder_id is explicitly None, filter for root files (folder_id IS NULL)
            query = query.filter(File.folder_id.is_(None))
        return query.order_by(File.created_at.desc()).offset(skip).limit(limit).all()

    def count_all(
        self, tenant_id: UUID, current_only: bool = True
    ) -> int:
        """Count all files for a tenant."""
        from sqlalchemy import func

        query = self.db.query(func.count(File.id)).filter(File.tenant_id == tenant_id)
        if current_only:
            query = query.filter(File.is_current == True)
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
        """Delete a file (soft delete by setting is_current=False)."""
        file = self.get_by_id(file_id, tenant_id)
        if not file:
            return False
        file.is_current = False
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

