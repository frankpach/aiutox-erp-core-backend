"""Unit tests for FileRepository soft delete functionality."""

import pytest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models.file import File
from app.repositories.file_repository import FileRepository


class TestFileRepositorySoftDelete:
    """Tests for FileRepository soft delete methods."""

    def test_delete_sets_deleted_at(self, db_session, test_tenant):
        """Test that delete sets deleted_at timestamp."""
        # Arrange
        repo = FileRepository(db_session)
        file_data = {
            "tenant_id": test_tenant.id,
            "name": "test.pdf",
            "original_name": "test.pdf",
            "mime_type": "application/pdf",
            "size": 1024,
            "storage_backend": "local",
            "storage_path": "/test/path",
            "is_current": True,
        }
        file = repo.create(file_data)

        # Act
        result = repo.delete(file.id, test_tenant.id)

        # Assert
        assert result is True
        db_session.refresh(file)
        assert file.is_current is False
        assert file.deleted_at is not None
        assert isinstance(file.deleted_at, datetime)

    def test_restore_file_success(self, db_session, test_tenant):
        """Test restoring a deleted file."""
        # Arrange
        repo = FileRepository(db_session)
        file_data = {
            "tenant_id": test_tenant.id,
            "name": "test.pdf",
            "original_name": "test.pdf",
            "mime_type": "application/pdf",
            "size": 1024,
            "storage_backend": "local",
            "storage_path": "/test/path",
            "is_current": False,
            "deleted_at": datetime.now(UTC),
        }
        file = repo.create(file_data)

        # Act
        result = repo.restore(file.id, test_tenant.id)

        # Assert
        assert result is True
        db_session.refresh(file)
        assert file.is_current is True
        assert file.deleted_at is None

    def test_restore_file_not_deleted(self, db_session, test_tenant):
        """Test restoring a file that was never deleted."""
        # Arrange
        repo = FileRepository(db_session)
        file_data = {
            "tenant_id": test_tenant.id,
            "name": "test.pdf",
            "original_name": "test.pdf",
            "mime_type": "application/pdf",
            "size": 1024,
            "storage_backend": "local",
            "storage_path": "/test/path",
            "is_current": True,
            "deleted_at": None,
        }
        file = repo.create(file_data)

        # Act
        result = repo.restore(file.id, test_tenant.id)

        # Assert
        assert result is False  # Cannot restore a file that was never deleted

    def test_restore_file_not_found(self, db_session, test_tenant):
        """Test restoring a non-existent file."""
        # Arrange
        repo = FileRepository(db_session)
        fake_id = uuid4()

        # Act
        result = repo.restore(fake_id, test_tenant.id)

        # Assert
        assert result is False

    def test_get_deleted_files_for_cleanup(self, db_session, test_tenant):
        """Test getting deleted files for cleanup."""
        # Arrange
        repo = FileRepository(db_session)
        retention_days = 30
        cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)

        # Create files: one old deleted, one recent deleted, one not deleted
        old_deleted_file = repo.create({
            "tenant_id": test_tenant.id,
            "name": "old_deleted.pdf",
            "original_name": "old_deleted.pdf",
            "mime_type": "application/pdf",
            "size": 1024,
            "storage_backend": "local",
            "storage_path": "/test/old",
            "is_current": False,
            "deleted_at": cutoff_date - timedelta(days=1),  # Older than retention
        })

        recent_deleted_file = repo.create({
            "tenant_id": test_tenant.id,
            "name": "recent_deleted.pdf",
            "original_name": "recent_deleted.pdf",
            "mime_type": "application/pdf",
            "size": 1024,
            "storage_backend": "local",
            "storage_path": "/test/recent",
            "is_current": False,
            "deleted_at": datetime.now(UTC) - timedelta(days=5),  # Recent
        })

        current_file = repo.create({
            "tenant_id": test_tenant.id,
            "name": "current.pdf",
            "original_name": "current.pdf",
            "mime_type": "application/pdf",
            "size": 1024,
            "storage_backend": "local",
            "storage_path": "/test/current",
            "is_current": True,
            "deleted_at": None,
        })

        # Act
        files_to_cleanup = repo.get_deleted_files_for_cleanup(test_tenant.id, retention_days)

        # Assert
        assert len(files_to_cleanup) == 1
        assert files_to_cleanup[0].id == old_deleted_file.id
        assert recent_deleted_file.id not in [f.id for f in files_to_cleanup]
        assert current_file.id not in [f.id for f in files_to_cleanup]

    def test_get_by_id_excludes_deleted_when_current_only_true(self, db_session, test_tenant):
        """Test that get_by_id excludes deleted files when current_only=True."""
        # Arrange
        repo = FileRepository(db_session)
        deleted_file = repo.create({
            "tenant_id": test_tenant.id,
            "name": "deleted.pdf",
            "original_name": "deleted.pdf",
            "mime_type": "application/pdf",
            "size": 1024,
            "storage_backend": "local",
            "storage_path": "/test/deleted",
            "is_current": False,
            "deleted_at": datetime.now(UTC),
        })

        current_file = repo.create({
            "tenant_id": test_tenant.id,
            "name": "current.pdf",
            "original_name": "current.pdf",
            "mime_type": "application/pdf",
            "size": 1024,
            "storage_backend": "local",
            "storage_path": "/test/current",
            "is_current": True,
            "deleted_at": None,
        })

        # Act
        result_deleted = repo.get_by_id(deleted_file.id, test_tenant.id, current_only=True)
        result_current = repo.get_by_id(current_file.id, test_tenant.id, current_only=True)
        result_deleted_with_current_only_false = repo.get_by_id(deleted_file.id, test_tenant.id, current_only=False)

        # Assert
        assert result_deleted is None  # Deleted file excluded
        assert result_current is not None  # Current file found
        assert result_deleted_with_current_only_false is not None  # Can find deleted when current_only=False

    def test_get_all_excludes_deleted_when_current_only_true(self, db_session, test_tenant):
        """Test that get_all excludes deleted files when current_only=True."""
        # Arrange
        repo = FileRepository(db_session)
        
        # Create a file and then delete it (proper soft delete flow)
        deleted_file = repo.create({
            "tenant_id": test_tenant.id,
            "name": "deleted.pdf",
            "original_name": "deleted.pdf",
            "mime_type": "application/pdf",
            "size": 1024,
            "storage_backend": "local",
            "storage_path": "/test/deleted",
            "is_current": True,  # Initially current
            "deleted_at": None,
        })
        
        # Properly soft delete the file
        repo.delete(deleted_file.id, test_tenant.id)
        
        current_file = repo.create({
            "tenant_id": test_tenant.id,
            "name": "current.pdf",
            "original_name": "current.pdf",
            "mime_type": "application/pdf",
            "size": 1024,
            "storage_backend": "local",
            "storage_path": "/test/current",
            "is_current": True,
            "deleted_at": None,
        })

        # Act
        all_files_current = repo.get_all(test_tenant.id, current_only=True)
        all_files_including_deleted = repo.get_all(test_tenant.id, current_only=False)

        # Assert
        assert len(all_files_current) == 1
        assert all_files_current[0].id == current_file.id
        assert deleted_file.id not in [f.id for f in all_files_current]

        # When current_only=False, should include deleted files
        # (because is_current filter is not applied)
        assert deleted_file.id in [f.id for f in all_files_including_deleted]
        assert len(all_files_including_deleted) == 2

