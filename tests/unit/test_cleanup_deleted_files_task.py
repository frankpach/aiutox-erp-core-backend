"""Unit tests for CleanupDeletedFilesTask."""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from app.core.files.tasks import CleanupDeletedFilesTask


class TestCleanupDeletedFilesTask:
    """Tests for CleanupDeletedFilesTask."""

    @pytest.fixture
    def task(self):
        """Create task instance."""
        return CleanupDeletedFilesTask(
            module="files",
            name="cleanup_deleted_files",
            description="Clean up deleted files"
        )

    @pytest.mark.asyncio
    async def test_execute_cleanup_success(self, task, db_session, test_tenant):
        """Test executing cleanup task successfully."""
        # Arrange
        from app.repositories.file_repository import FileRepository
        repo = FileRepository(db_session)

        retention_days = 30
        old_deleted_file = repo.create({
            "tenant_id": test_tenant.id,
            "name": "old_deleted.pdf",
            "original_name": "old_deleted.pdf",
            "mime_type": "application/pdf",
            "size": 2048,
            "storage_backend": "local",
            "storage_path": "/test/old",
            "is_current": False,
            "deleted_at": datetime.now(UTC) - timedelta(days=retention_days + 1),
        })

        # Mock FileService
        with patch("app.core.files.tasks.FileService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.cleanup_deleted_files = AsyncMock(return_value={
                "files_count": 1,
                "storage_freed": 2048,
                "errors": [],
            })
            mock_service_class.return_value = mock_service

            # Mock get_db
            with patch("app.core.files.tasks.get_db") as mock_get_db:
                mock_db_gen = iter([db_session])
                mock_get_db.return_value = mock_db_gen

                # Act
                result = await task.execute(test_tenant.id, retention_days=retention_days)

                # Assert
                assert result["files_deleted"] == 1
                assert result["storage_freed"] == 2048
                assert len(result["errors"]) == 0
                assert result["tenant_id"] == str(test_tenant.id)
                mock_service.cleanup_deleted_files.assert_called_once_with(
                    test_tenant.id, retention_days
                )

    @pytest.mark.asyncio
    async def test_execute_cleanup_with_errors(self, task, db_session, test_tenant):
        """Test executing cleanup task with errors."""
        # Arrange
        with patch("app.core.files.tasks.FileService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.cleanup_deleted_files = AsyncMock(return_value={
                "files_count": 0,
                "storage_freed": 0,
                "errors": [{"file_id": str(uuid4()), "error": "Storage error"}],
            })
            mock_service_class.return_value = mock_service

            with patch("app.core.files.tasks.get_db") as mock_get_db:
                mock_db_gen = iter([db_session])
                mock_get_db.return_value = mock_db_gen

                # Act
                result = await task.execute(test_tenant.id)

                # Assert
                assert result["files_deleted"] == 0
                assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_execute_cleanup_handles_exceptions(self, task, db_session, test_tenant):
        """Test that task handles exceptions gracefully."""
        # Arrange
        with patch("app.core.files.tasks.FileService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.cleanup_deleted_files = AsyncMock(side_effect=Exception("Service error"))
            mock_service_class.return_value = mock_service

            with patch("app.core.files.tasks.get_db") as mock_get_db:
                mock_db_gen = iter([db_session])
                mock_get_db.return_value = mock_db_gen

                # Act & Assert
                with pytest.raises(Exception, match="Service error"):
                    await task.execute(test_tenant.id)




