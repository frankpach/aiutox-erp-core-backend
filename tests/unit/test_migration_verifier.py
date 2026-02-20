"""Unit tests for MigrationVerifier."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.migrations.manager import MigrationManager
from app.core.migrations.models import (
    IntegrityResult,
    SchemaVerificationResult,
    VerificationResult,
)
from app.core.migrations.verifier import MigrationVerifier


@pytest.fixture
def mock_manager():
    """Create mock MigrationManager."""
    manager = MagicMock(spec=MigrationManager)
    manager.get_current_revision = MagicMock(return_value="001_test")
    manager.get_applied_migrations = MagicMock(return_value=[])
    manager._get_all_migration_files = MagicMock(return_value=[])
    return manager


@pytest.fixture
def verifier(mock_manager):
    """Create MigrationVerifier with mock manager."""
    return MigrationVerifier(manager=mock_manager)


def test_verify_applied_no_issues(verifier, mock_manager):
    """Test verify_applied with no issues."""
    mock_manager.get_current_revision = MagicMock(return_value="001_test")
    mock_manager.get_applied_migrations = MagicMock(
        return_value=[
            MagicMock(revision="001_test"),
        ]
    )
    mock_manager._get_all_migration_files = MagicMock(
        return_value=[
            MagicMock(revision="001_test"),
        ]
    )

    result = verifier.verify_applied()
    assert isinstance(result, VerificationResult)
    assert result.applied_match


def test_verify_applied_orphaned(verifier, mock_manager):
    """Test verify_applied with orphaned migrations."""
    mock_manager.get_current_revision = MagicMock(return_value="001_test")
    mock_manager.get_applied_migrations = MagicMock(
        return_value=[
            MagicMock(revision="001_test"),
            MagicMock(revision="999_orphaned"),
        ]
    )
    mock_manager._get_all_migration_files = MagicMock(
        return_value=[
            MagicMock(revision="001_test"),
        ]
    )

    result = verifier.verify_applied()
    assert not result.applied_match
    assert len(result.issues) > 0


def test_verify_schema(verifier):
    """Test verify_schema."""
    with patch("app.core.migrations.verifier.inspect") as mock_inspect:
        mock_inspector = MagicMock()
        mock_inspector.get_table_names = MagicMock(return_value=["users", "tenants"])
        mock_inspector.get_columns = MagicMock(return_value=[])
        mock_inspect.return_value = mock_inspector

        # Mock Base.metadata.tables properly
        from app.core.db.session import Base

        # Create proper mock columns
        mock_user_table = MagicMock()
        mock_user_col_id = MagicMock()
        mock_user_col_id.name = "id"
        mock_user_col_id.type = MagicMock()
        mock_user_col_email = MagicMock()
        mock_user_col_email.name = "email"
        mock_user_col_email.type = MagicMock()
        mock_user_table.columns = [mock_user_col_id, mock_user_col_email]

        mock_tenant_table = MagicMock()
        mock_tenant_col_id = MagicMock()
        mock_tenant_col_id.name = "id"
        mock_tenant_col_id.type = MagicMock()
        mock_tenant_table.columns = [mock_tenant_col_id]

        with patch.object(Base.metadata, "tables", {
            "users": mock_user_table,
            "tenants": mock_tenant_table,
        }):
            result = verifier.verify_schema()
            assert isinstance(result, SchemaVerificationResult)


def test_verify_integrity_valid(verifier, mock_manager):
    """Test verify_integrity with valid chain."""
    from pathlib import Path

    # Create a proper mock script_dir
    mock_script_dir = MagicMock()
    mock_versions_dir = Path(__file__).parent.parent.parent / "migrations" / "versions"
    mock_script_dir.versions = mock_versions_dir
    verifier.manager.script_dir = mock_script_dir

    result = verifier.verify_integrity()
    assert isinstance(result, IntegrityResult)


def test_get_orphaned_migrations(verifier, mock_manager):
    """Test get_orphaned_migrations."""
    mock_manager.get_applied_migrations = MagicMock(
        return_value=[
            MagicMock(revision="001_test"),
            MagicMock(revision="999_orphaned"),
        ]
    )
    mock_manager._get_all_migration_files = MagicMock(
        return_value=[
            MagicMock(revision="001_test"),
        ]
    )

    orphaned = verifier.get_orphaned_migrations()
    assert "999_orphaned" in orphaned


def test_get_missing_tables(verifier):
    """Test get_missing_tables."""
    with patch("app.core.migrations.verifier.MigrationVerifier.verify_schema") as mock_verify:
        mock_result = MagicMock()
        mock_result.diff.missing_tables = ["missing_table"]
        mock_verify.return_value = mock_result

        missing = verifier.get_missing_tables()
        assert "missing_table" in missing


def test_verify_all(verifier):
    """Test verify_all."""
    with patch("app.core.migrations.verifier.MigrationVerifier.verify_applied") as mock_applied, patch(
        "app.core.migrations.verifier.MigrationVerifier.verify_schema"
    ) as mock_schema, patch(
        "app.core.migrations.verifier.MigrationVerifier.verify_integrity"
    ) as mock_integrity:
        mock_applied.return_value = VerificationResult(
            applied_match=True, schema_match=True, integrity_ok=True
        )
        mock_schema.return_value = MagicMock(match=True, issues=[], diff=MagicMock())
        mock_integrity.return_value = IntegrityResult(valid=True, errors=[], warnings=[])

        result = verifier.verify_all()
        assert isinstance(result, VerificationResult)

