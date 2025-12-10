"""Migration verifier for checking migration status and schema integrity."""

import re
from pathlib import Path
from typing import List, Tuple

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.core.config import get_settings
from app.core.db.session import Base, engine
from app.core.migrations.manager import MigrationManager
from app.core.migrations.models import (
    IntegrityResult,
    SchemaDiff,
    SchemaVerificationResult,
    VerificationResult,
)


class MigrationVerifier:
    """Verifier for migration status and schema integrity."""

    def __init__(self, manager: MigrationManager | None = None):
        """Initialize migration verifier.

        Args:
            manager: MigrationManager instance. If None, creates a new one.
        """
        self.manager = manager or MigrationManager()
        self.settings = get_settings()
        self.engine = engine

    def verify_applied(self) -> VerificationResult:
        """Verify that applied migrations match migration files.

        Returns:
            VerificationResult object
        """
        issues = []
        applied_match = True

        # Get applied migrations from DB
        current_revision = self.manager.get_current_revision()
        applied_migrations = self.manager.get_applied_migrations()
        all_migrations = self.manager._get_all_migration_files()

        # Check if current revision exists in files
        if current_revision:
            revision_in_files = any(m.revision == current_revision for m in all_migrations)
            if not revision_in_files:
                applied_match = False
                issues.append(
                    f"Current revision {current_revision} not found in migration files"
                )

        # Check for orphaned migrations (in DB but not in files)
        all_revision_ids = {m.revision for m in all_migrations}
        applied_revision_ids = {m.revision for m in applied_migrations}

        orphaned = applied_revision_ids - all_revision_ids
        if orphaned:
            applied_match = False
            issues.append(f"Orphaned migrations in DB (not in files): {orphaned}")

        return VerificationResult(
            applied_match=applied_match,
            schema_match=True,  # Will be set by verify_schema
            integrity_ok=True,  # Will be set by verify_integrity
            issues=issues,
        )

    def verify_schema(self) -> SchemaVerificationResult:
        """Verify that database schema matches SQLAlchemy models.

        Returns:
            SchemaVerificationResult object
        """
        inspector = inspect(self.engine)
        db_tables = set(inspector.get_table_names())

        # Get expected tables from models
        expected_tables = set(Base.metadata.tables.keys())

        diff = SchemaDiff()
        issues = []

        # Find missing tables
        missing_tables = expected_tables - db_tables
        if missing_tables:
            diff.missing_tables = list(missing_tables)
            issues.append(f"Missing tables: {missing_tables}")

        # Find extra tables (ignore alembic_version)
        extra_tables = db_tables - expected_tables - {"alembic_version"}
        if extra_tables:
            diff.extra_tables = list(extra_tables)
            issues.append(f"Extra tables in DB: {extra_tables}")

        # Check columns for each expected table
        for table_name in expected_tables:
            if table_name not in db_tables:
                continue  # Already reported as missing

            model_table = Base.metadata.tables[table_name]
            db_columns = {col["name"]: col for col in inspector.get_columns(table_name)}
            model_columns = {col.name: col for col in model_table.columns}

            # Find missing columns
            missing_cols = set(model_columns.keys()) - set(db_columns.keys())
            if missing_cols:
                for col_name in missing_cols:
                    diff.missing_columns.append((table_name, col_name))
                    issues.append(f"Missing column {table_name}.{col_name}")

            # Find extra columns
            extra_cols = set(db_columns.keys()) - set(model_columns.keys())
            if extra_cols:
                for col_name in extra_cols:
                    diff.extra_columns.append((table_name, col_name))
                    issues.append(f"Extra column {table_name}.{col_name}")

            # Check column types (basic check)
            for col_name in set(model_columns.keys()) & set(db_columns.keys()):
                model_col = model_columns[col_name]
                db_col = db_columns[col_name]

                # Compare types (simplified - just check if they're different)
                model_type_str = str(model_col.type)
                db_type_str = str(db_col["type"])

                # Normalize type strings for comparison
                model_type_normalized = model_type_str.lower().replace(" ", "")
                db_type_normalized = db_type_str.lower().replace(" ", "")

                # Skip if types are similar enough (UUID vs uuid, etc.)
                if model_type_normalized != db_type_normalized:
                    # Check if they're just different representations
                    if not (
                        "uuid" in model_type_normalized and "uuid" in db_type_normalized
                        or "varchar" in model_type_normalized
                        and "varchar" in db_type_normalized
                        or "text" in model_type_normalized
                        and "text" in db_type_normalized
                    ):
                        diff.column_type_mismatches.append(
                            (table_name, col_name, model_type_str, db_type_str)
                        )
                        issues.append(
                            f"Type mismatch {table_name}.{col_name}: "
                            f"expected {model_type_str}, got {db_type_str}"
                        )

        match = len(issues) == 0

        return SchemaVerificationResult(
            match=match,
            diff=diff,
            issues=issues,
        )

    def verify_integrity(self) -> IntegrityResult:
        """Verify migration chain integrity.

        Returns:
            IntegrityResult object
        """
        errors = []
        warnings = []

        # Get migrations directory
        versions_dir = Path(self.manager.script_dir.versions)

        if not versions_dir.exists():
            return IntegrityResult(
                valid=False,
                errors=["Migrations directory not found"],
            )

        # Find all migration files
        migration_files = sorted(versions_dir.glob("*.py"))

        if not migration_files:
            return IntegrityResult(
                valid=False,
                errors=["No migration files found"],
            )

        # Extract revision IDs and dependencies
        revisions = {}
        for file_path in migration_files:
            if file_path.name in ("__init__.py", "env.py"):
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract revision
                revision_match = re.search(
                    r'revision\s*:\s*[^=]*=\s*["\']([^"\']+)["\']|revision\s*=\s*["\']([^"\']+)["\']',
                    content,
                )
                if not revision_match:
                    errors.append(f"{file_path.name}: Could not find revision ID")
                    continue

                revision_id = revision_match.group(1) or revision_match.group(2)

                # Extract down_revision
                down_revision_match = re.search(
                    r'down_revision\s*:\s*[^=]*=\s*["\']?([^"\',\s\)]+)["\']?|down_revision\s*=\s*["\']?([^"\',\s\)]+)["\']?',
                    content,
                )
                down_revision = None
                if down_revision_match:
                    down_revision = down_revision_match.group(1) or down_revision_match.group(2)
                    if down_revision and down_revision.strip() in ("None", "null"):
                        down_revision = None

                revisions[revision_id] = {
                    "file": file_path.name,
                    "down_revision": down_revision,
                }
            except Exception as e:
                errors.append(f"{file_path.name}: Error parsing - {e}")

        # Check chain
        if not revisions:
            return IntegrityResult(
                valid=False,
                errors=["No valid revisions found"],
            )

        # Find root (revision with down_revision = None)
        root_revisions = [
            rev_id for rev_id, info in revisions.items() if info["down_revision"] is None
        ]

        if len(root_revisions) != 1:
            errors.append(
                f"Expected exactly one root revision, found {len(root_revisions)}"
            )

        # Check that all revisions are connected
        visited = set()
        current = root_revisions[0] if root_revisions else None

        while current:
            if current in visited:
                errors.append(f"Circular dependency detected: {current}")
                break
            visited.add(current)
            # Find next revision
            next_rev = None
            for rev_id, info in revisions.items():
                if info["down_revision"] == current:
                    if next_rev:
                        errors.append(f"Multiple revisions depend on {current}")
                        break
                    next_rev = rev_id
            current = next_rev

        missing = set(revisions.keys()) - visited
        if missing:
            warnings.append(f"Orphaned revisions (not in chain): {missing}")

        return IntegrityResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def get_orphaned_migrations(self) -> List[str]:
        """Get list of orphaned migrations (in DB but not in files).

        Returns:
            List of orphaned revision IDs
        """
        applied_migrations = self.manager.get_applied_migrations()
        all_migrations = self.manager._get_all_migration_files()

        all_revision_ids = {m.revision for m in all_migrations}
        applied_revision_ids = {m.revision for m in applied_migrations}

        orphaned = applied_revision_ids - all_revision_ids
        return list(orphaned)

    def get_missing_tables(self) -> List[str]:
        """Get list of missing tables (expected but not in DB).

        Returns:
            List of missing table names
        """
        schema_result = self.verify_schema()
        return schema_result.diff.missing_tables

    def verify_all(self) -> VerificationResult:
        """Run all verification checks.

        Returns:
            Complete VerificationResult
        """
        applied_result = self.verify_applied()
        schema_result = self.verify_schema()
        integrity_result = self.verify_integrity()

        all_issues = (
            applied_result.issues
            + schema_result.issues
            + integrity_result.errors
            + integrity_result.warnings
        )

        return VerificationResult(
            applied_match=applied_result.applied_match,
            schema_match=schema_result.match,
            integrity_ok=integrity_result.valid,
            issues=all_issues,
            schema_diff=schema_result.diff,
        )

