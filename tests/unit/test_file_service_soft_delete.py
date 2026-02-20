"""Unit tests for FileService soft delete functionality."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.files.service import FileService


class TestFileServiceSoftDelete:
    """Tests for FileService soft delete methods."""

    @pytest.fixture
    def mock_storage_backend(self):
        """Mock storage backend."""
        backend = AsyncMock()
        backend.delete = AsyncMock()
        return backend

    @pytest.fixture
    def mock_event_publisher(self):
        """Mock event publisher."""
        return AsyncMock()

    @pytest.fixture
    def file_service(
        self, db_session, test_tenant, mock_storage_backend, mock_event_publisher
    ):
        """Create FileService instance."""
        with patch(
            "app.core.files.service.StorageConfigService"
        ) as mock_config_service:
            mock_config_service.return_value.get_file_limits.return_value = {
                "retention_days": 30
            }
            service = FileService(
                db_session,
                storage_backend=mock_storage_backend,
                event_publisher=mock_event_publisher,
                tenant_id=test_tenant.id,
            )
            service._storage_config_service = mock_config_service.return_value
            return service

    @pytest.mark.asyncio
    async def test_cleanup_deleted_files_success(
        self,
        file_service,
        db_session,
        test_tenant,
        mock_storage_backend,
        mock_event_publisher,
    ):
        """Test cleanup of deleted files."""
        # Arrange
        from app.repositories.file_repository import FileRepository

        repo = FileRepository(db_session)

        retention_days = 30
        old_deleted_file = repo.create(
            {
                "tenant_id": test_tenant.id,
                "name": "old_deleted.pdf",
                "original_name": "old_deleted.pdf",
                "mime_type": "application/pdf",
                "size": 2048,
                "storage_backend": "local",
                "storage_path": "/test/old",
                "is_current": False,
                "deleted_at": datetime.now(UTC) - timedelta(days=retention_days + 1),
            }
        )

        # Create a version for the file
        from app.models.file import FileVersion

        version = FileVersion(
            id=uuid4(),
            file_id=old_deleted_file.id,
            tenant_id=test_tenant.id,
            version_number=1,
            storage_path="/test/old/v1",
            storage_backend="local",
            size=1024,
            mime_type="application/pdf",
        )
        db_session.add(version)
        db_session.commit()

        # Mock repository methods to return our test data
        file_service.repository.get_deleted_files_for_cleanup = MagicMock(
            return_value=[old_deleted_file]
        )
        file_service.repository.get_versions = MagicMock(return_value=[version])

        # Act
        result = await file_service.cleanup_deleted_files(
            test_tenant.id, retention_days
        )

        # Assert
        assert result["files_count"] == 1
        assert result["storage_freed"] == 2048
        assert len(result["errors"]) == 0
        # Verify storage backend was called
        assert mock_storage_backend.delete.call_count >= 1
        # Verify event was published
        mock_event_publisher.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_deleted_files_with_errors(
        self, file_service, db_session, test_tenant, mock_storage_backend
    ):
        """Test cleanup handles errors gracefully."""
        # Arrange
        from app.repositories.file_repository import FileRepository

        repo = FileRepository(db_session)

        old_deleted_file = repo.create(
            {
                "tenant_id": test_tenant.id,
                "name": "old_deleted.pdf",
                "original_name": "old_deleted.pdf",
                "mime_type": "application/pdf",
                "size": 2048,
                "storage_backend": "local",
                "storage_path": "/test/old",
                "is_current": True,  # Initially current
                "deleted_at": datetime.now(UTC)
                - timedelta(days=31),  # But marked as deleted long ago
            }
        )

        # Store the file ID before any potential deletion
        file_id = old_deleted_file.id

        # Mock storage to raise error
        mock_storage_backend.delete.side_effect = Exception("Storage error")

        file_service.repository.get_deleted_files_for_cleanup = MagicMock(
            return_value=[old_deleted_file]
        )
        file_service.repository.get_versions = MagicMock(return_value=[])

        # Act
        result = await file_service.cleanup_deleted_files(test_tenant.id, 30)

        # Assert
        assert result["files_count"] == 0
        assert result["storage_freed"] == 0
        assert len(result["errors"]) == 1
        assert result["errors"][0]["file_id"] == str(file_id)

    @pytest.mark.asyncio
    async def test_cleanup_deleted_files_uses_config_retention(
        self, file_service, db_session, test_tenant
    ):
        """Test cleanup uses retention_days from config if not provided."""
        # Arrange
        file_service._storage_config_service.get_file_limits.return_value = {
            "retention_days": 60
        }
        file_service.repository.get_deleted_files_for_cleanup = MagicMock(
            return_value=[]
        )

        # Act
        await file_service.cleanup_deleted_files(test_tenant.id)

        # Assert
        file_service.repository.get_deleted_files_for_cleanup.assert_called_once_with(
            test_tenant.id, 60
        )

    @pytest.mark.asyncio
    async def test_restore_file_success(
        self, file_service, db_session, test_tenant, mock_event_publisher
    ):
        """Test restoring a deleted file."""
        # Arrange
        from app.repositories.file_repository import FileRepository

        repo = FileRepository(db_session)

        deleted_file = repo.create(
            {
                "tenant_id": test_tenant.id,
                "name": "deleted.pdf",
                "original_name": "deleted.pdf",
                "mime_type": "application/pdf",
                "size": 1024,
                "storage_backend": "local",
                "storage_path": "/test/deleted",
                "is_current": False,
                "deleted_at": datetime.now(UTC),
            }
        )

        # Act
        result = await file_service.restore_file(
            deleted_file.id, test_tenant.id, uuid4()
        )

        # Assert
        assert result is True
        db_session.refresh(deleted_file)
        assert deleted_file.is_current is True
        assert deleted_file.deleted_at is None
        mock_event_publisher.publish.assert_called_once()
        call_args = mock_event_publisher.publish.call_args
        assert call_args.kwargs["event_type"] == "file.restored"

    @pytest.mark.asyncio
    async def test_restore_file_not_found(self, file_service, test_tenant):
        """Test restoring a non-existent file."""
        # Act
        result = await file_service.restore_file(uuid4(), test_tenant.id, uuid4())

        # Assert
        assert result is False
