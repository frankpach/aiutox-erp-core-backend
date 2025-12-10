"""Tests for make commands."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from scripts.cli.commands.make import app
from scripts.cli.utils.generators import generate_model


class TestMakeCommands:
    """Tests for make commands."""

    @patch("scripts.cli.commands.make.generate_model")
    def test_make_model_command(self, mock_generate):
        """Test make:model command."""
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["model", "TestModel"])

        assert result.exit_code == 0
        mock_generate.assert_called_once_with("TestModel")

    @patch("scripts.cli.commands.make.generate_service")
    def test_make_service_command(self, mock_generate):
        """Test make:service command."""
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["service", "TestService"])

        assert result.exit_code == 0
        mock_generate.assert_called_once_with("TestService")

    @patch("scripts.cli.commands.make.generate_repository")
    def test_make_repository_command(self, mock_generate):
        """Test make:repository command."""
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["repository", "TestRepository"])

        assert result.exit_code == 0
        mock_generate.assert_called_once_with("TestRepository")

    @patch("scripts.cli.commands.make.generate_router")
    def test_make_router_command(self, mock_generate):
        """Test make:router command."""
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["router", "TestRouter"])

        assert result.exit_code == 0
        mock_generate.assert_called_once_with("TestRouter")

    @patch("scripts.cli.commands.make.generate_schema")
    def test_make_schema_command(self, mock_generate):
        """Test make:schema command."""
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["schema", "TestSchema"])

        assert result.exit_code == 0
        mock_generate.assert_called_once_with("TestSchema")

    @patch("scripts.cli.commands.make.generate_seeder")
    def test_make_seeder_command(self, mock_generate):
        """Test make:seeder command."""
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["seeder", "TestSeeder"])

        assert result.exit_code == 0
        mock_generate.assert_called_once_with("TestSeeder")

    @patch("scripts.cli.commands.make.generate_module")
    def test_make_module_command(self, mock_generate):
        """Test make:module command."""
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["module", "TestModule"])

        assert result.exit_code == 0
        mock_generate.assert_called_once_with("TestModule", None)

    @patch("scripts.cli.commands.make.generate_module")
    def test_make_module_with_entities(self, mock_generate):
        """Test make:module command with entities."""
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["module", "TestModule", "--entities", "Entity1,Entity2"])

        assert result.exit_code == 0
        mock_generate.assert_called_once_with("TestModule", ["Entity1", "Entity2"])

