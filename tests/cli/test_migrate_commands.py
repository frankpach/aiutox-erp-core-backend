"""Tests for migrate commands."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from scripts.cli.commands.migrate import app  # noqa: E402


class TestMigrateCommands:
    """Tests for migrate commands."""

    @patch("scripts.cli.commands.migrate.handle_migrate")
    def test_migrate_apply_command(self, mock_handle):
        """Test migrate apply command."""
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["apply"])

        assert result.exit_code == 0
        mock_handle.assert_called_once()

    @patch("scripts.cli.commands.migrate.handle_status")
    def test_migrate_status_command(self, mock_handle):
        """Test migrate status command."""
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        mock_handle.assert_called_once()

    @patch("scripts.cli.commands.migrate.handle_verify")
    def test_migrate_verify_command(self, mock_handle):
        """Test migrate verify command."""
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["verify"])

        assert result.exit_code == 0
        mock_handle.assert_called_once()

    @patch("scripts.cli.commands.migrate.MigrationManager")
    def test_migrate_rollback_command(self, mock_manager_class):
        """Test migrate rollback command."""
        from typer.testing import CliRunner

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_status.return_value.applied = [MagicMock()]

        runner = CliRunner()
        result = runner.invoke(app, ["rollback", "--steps", "2", "--yes"])

        # Should call rollback
        assert mock_manager.rollback.called
        assert result.exit_code == 0

