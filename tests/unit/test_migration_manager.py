"""Unit tests for MigrationManager."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.core.migrations.manager import MigrationManager
from app.core.migrations.models import MigrationInfo, MigrationResult, MigrationStatus


@pytest.fixture
def mock_alembic_cfg():
    """Mock Alembic config."""
    mock_cfg = MagicMock()
    mock_cfg.set_main_option = MagicMock()
    return mock_cfg


@pytest.fixture
def mock_script_dir():
    """Mock script directory."""
    mock_dir = MagicMock()
    mock_dir.versions = Path(__file__).parent.parent.parent / "migrations" / "versions"
    mock_dir.get_current_head = MagicMock(return_value="002_test")
    return mock_dir


@pytest.fixture
def manager(mock_alembic_cfg, mock_script_dir):
    """Create MigrationManager with mocks."""
    with patch("app.core.migrations.manager.config.Config", return_value=mock_alembic_cfg), patch(
        "app.core.migrations.manager.script.ScriptDirectory.from_config", return_value=mock_script_dir
    ), patch("app.core.migrations.manager.engine"):
        manager = MigrationManager()
        manager.alembic_cfg = mock_alembic_cfg
        manager.script_dir = mock_script_dir
        return manager


def test_get_current_revision(manager):
    """Test getting current revision."""
    with patch("app.core.migrations.manager.MigrationContext") as mock_context_class:
        mock_context = MagicMock()
        mock_context.get_current_revision = MagicMock(return_value="001_test")
        mock_context_class.configure = MagicMock(return_value=mock_context)

        revision = manager.get_current_revision()
        assert revision == "001_test"


def test_get_current_revision_none(manager):
    """Test getting current revision when none exists."""
    with patch("app.core.migrations.manager.MigrationContext") as mock_context_class:
        mock_context = MagicMock()
        mock_context.get_current_revision = MagicMock(return_value=None)
        mock_context_class.configure = MagicMock(return_value=mock_context)

        revision = manager.get_current_revision()
        assert revision is None


def test_get_applied_migrations_empty(manager):
    """Test getting applied migrations when none exist."""
    manager.get_current_revision = MagicMock(return_value=None)
    applied = manager.get_applied_migrations()
    assert applied == []


def test_get_pending_migrations_all_pending(manager):
    """Test getting pending migrations when none are applied."""
    manager.get_current_revision = MagicMock(return_value=None)
    all_migrations = [
        MigrationInfo(
            revision="001_test",
            down_revision=None,
            file="001_test.py",
            applied=False,
        ),
        MigrationInfo(
            revision="002_test",
            down_revision="001_test",
            file="002_test.py",
            applied=False,
        ),
    ]
    manager._get_all_migration_files = MagicMock(return_value=all_migrations)

    pending = manager.get_pending_migrations()
    assert len(pending) == 2
    assert all(not m.applied for m in pending)


def test_get_status(manager):
    """Test getting migration status."""
    manager.get_current_revision = MagicMock(return_value="001_test")
    manager.get_applied_migrations = MagicMock(return_value=[])
    manager.get_pending_migrations = MagicMock(return_value=[])

    status = manager.get_status()
    assert isinstance(status, MigrationStatus)
    assert status.current_revision == "001_test"


def test_create_migration(manager):
    """Test creating a new migration."""
    with patch("app.core.migrations.manager.command.revision") as mock_revision, patch(
        "sys.stdout"
    ):
        mock_revision.return_value = None
        result = manager.create_migration("test migration", autogenerate=True)
        mock_revision.assert_called_once()
        assert "Migration created" in result or "migrations" in result.lower()


def test_rollback_no_migrations(manager):
    """Test rollback when no migrations exist."""
    manager.get_current_revision = MagicMock(return_value=None)
    result = manager.rollback()
    assert not result.success
    assert "No migrations to rollback" in result.errors[0]


def test_fresh(manager):
    """Test fresh command."""
    with patch.object(manager, "apply_migrations") as mock_apply, patch.object(
        manager, "engine"
    ) as mock_engine:
        # Mock the engine connection context manager
        mock_connection = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_connection)
        mock_context.__exit__ = MagicMock(return_value=False)
        mock_engine.begin.return_value = mock_context

        # Mock execute to return table names
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([("table1",), ("table2",)]))
        mock_connection.execute.return_value = mock_result

        mock_apply.return_value = MigrationResult(success=True, applied_count=3)
        result = manager.fresh()
        mock_apply.assert_called_once()
        assert result.success


def test_refresh(manager):
    """Test refresh command."""
    with patch("app.core.migrations.manager.MigrationManager.rollback") as mock_rollback, patch(
        "app.core.migrations.manager.MigrationManager.apply_migrations"
    ) as mock_apply:
        mock_rollback.return_value = MigrationResult(success=True, applied_count=-2)
        mock_apply.return_value = MigrationResult(success=True, applied_count=2)
        result = manager.refresh()
        mock_rollback.assert_called_once()
        mock_apply.assert_called_once()
        assert result.success





