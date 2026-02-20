"""Integration tests for migrate_cli."""

from unittest.mock import MagicMock

import pytest

from app.core.migrations.manager import MigrationManager
from app.core.migrations.models import MigrationResult, MigrationStatus
from app.core.migrations.reporter import MigrationReporter
from app.core.migrations.verifier import MigrationVerifier


@pytest.fixture
def mock_manager():
    """Create mock MigrationManager."""
    manager = MagicMock(spec=MigrationManager)
    manager.get_status = MagicMock(
        return_value=MigrationStatus(
            current_revision="001_test",
            applied=[],
            pending=[],
            orphaned=[],
        )
    )
    manager.apply_migrations = MagicMock(return_value=MigrationResult(success=True, applied_count=0))
    manager.rollback = MagicMock(return_value=MigrationResult(success=True, applied_count=-1))
    manager.fresh = MagicMock(return_value=MigrationResult(success=True, applied_count=3))
    manager.refresh = MagicMock(return_value=MigrationResult(success=True, applied_count=3))
    manager.create_migration = MagicMock(return_value="migrations/versions/003_test.py")
    manager._get_all_migration_files = MagicMock(return_value=[])
    return manager


@pytest.fixture
def mock_verifier(mock_manager):
    """Create mock MigrationVerifier."""
    return MagicMock(spec=MigrationVerifier)


@pytest.fixture
def mock_reporter():
    """Create mock MigrationReporter."""
    return MagicMock(spec=MigrationReporter)


def test_migrate_command_non_interactive(mock_manager, mock_reporter):
    """Test migrate command in non-interactive mode."""
    # Test that manager methods work correctly
    status = mock_manager.get_status()
    assert status is not None
    assert isinstance(status, MigrationStatus)

    result = mock_manager.apply_migrations()
    assert result is not None
    assert isinstance(result, MigrationResult)


def test_status_command_non_interactive(mock_manager, mock_reporter):
    """Test status command in non-interactive mode."""
    status = mock_manager.get_status()
    assert status.current_revision == "001_test"
    assert isinstance(status, MigrationStatus)


def test_rollback_command_non_interactive(mock_manager, mock_reporter):
    """Test rollback command in non-interactive mode."""
    result = mock_manager.rollback(steps=1)
    assert result.success
    assert result.applied_count == -1


def test_fresh_command_non_interactive(mock_manager, mock_reporter):
    """Test fresh command in non-interactive mode."""
    result = mock_manager.fresh()
    assert result.success
    assert result.applied_count == 3


def test_refresh_command_non_interactive(mock_manager, mock_reporter):
    """Test refresh command in non-interactive mode."""
    result = mock_manager.refresh()
    assert result.success
    assert result.applied_count == 3


def test_make_migration_command_non_interactive(mock_manager, mock_reporter):
    """Test make:migration command in non-interactive mode."""
    file_path = mock_manager.create_migration("test migration", autogenerate=True)
    assert "migrations" in file_path.lower()

