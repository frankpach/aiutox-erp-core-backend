"""Migration manager for Alembic migrations."""

import re
from pathlib import Path

from alembic import command, config, script
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text

from app.core.config_file import get_settings
from app.core.db.session import engine
from app.core.migrations.models import MigrationInfo, MigrationResult, MigrationStatus


class MigrationManager:
    """Manager for Alembic migrations."""

    def __init__(self, alembic_cfg_path: Path | None = None):
        """Initialize migration manager.

        Args:
            alembic_cfg_path: Path to alembic.ini file. Defaults to backend/alembic.ini
        """
        if alembic_cfg_path is None:
            # Assume we're in backend directory
            backend_dir = Path(__file__).parent.parent.parent.parent
            alembic_cfg_path = backend_dir / "alembic.ini"

        self.alembic_cfg = config.Config(str(alembic_cfg_path))
        self.script_dir = script.ScriptDirectory.from_config(self.alembic_cfg)
        self.settings = get_settings()
        self.engine = engine

    def get_current_revision(self) -> str | None:
        """Get current revision from database.

        Returns:
            Current revision ID or None if no migrations applied.
            If multiple heads exist, returns the first one (for backward compatibility).
        """
        with self.engine.connect() as connection:
            context = MigrationContext.configure(connection)
            try:
                # Try to get single revision first (backward compatibility)
                return context.get_current_revision()
            except Exception:
                # If multiple heads exist, get all heads and return first one
                try:
                    heads = context.get_current_heads()
                    return heads[0] if heads else None
                except Exception:
                    # Fallback: try to get from script directory
                    try:
                        heads = self.script_dir.get_heads()
                        return heads[0] if heads else None
                    except Exception:
                        return None

    def _get_migration_info_from_file(self, file_path: Path) -> MigrationInfo | None:
        """Extract migration info from a migration file.

        Args:
            file_path: Path to migration file

        Returns:
            MigrationInfo or None if file cannot be parsed
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Extract revision
            revision_match = re.search(
                r'revision\s*:\s*[^=]*=\s*["\']([^"\']+)["\']|revision\s*=\s*["\']([^"\']+)["\']',
                content,
            )
            if not revision_match:
                return None

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

            # Extract description from docstring or comment
            description_match = re.search(
                r'"""([^"]+)"""|Revision ID: ([^\n]+)',
                content,
            )
            description = None
            if description_match:
                description = description_match.group(1) or description_match.group(2)

            return MigrationInfo(
                revision=revision_id,
                down_revision=down_revision,
                file=file_path.name,
                applied=False,  # Will be set later
                description=description,
            )
        except Exception:
            return None

    def _get_all_migration_files(self) -> list[MigrationInfo]:
        """Get all migration files from versions directory.

        Returns:
            List of MigrationInfo objects
        """
        versions_dir = Path(self.script_dir.versions)
        migrations = []

        for file_path in sorted(versions_dir.glob("*.py")):
            if file_path.name in ("__init__.py", "env.py"):
                continue

            migration_info = self._get_migration_info_from_file(file_path)
            if migration_info:
                migrations.append(migration_info)

        return migrations

    def get_applied_migrations(self) -> list[MigrationInfo]:
        """Get list of applied migrations.

        Returns:
            List of applied MigrationInfo objects
        """
        current_revision = self.get_current_revision()
        if not current_revision:
            return []

        all_migrations = self._get_all_migration_files()
        applied = []

        # Build chain from current revision backwards
        revision_map = {m.revision: m for m in all_migrations}
        visited = set()

        def add_migration_and_ancestors(rev: str):
            if rev in visited or rev not in revision_map:
                return
            visited.add(rev)
            migration = revision_map[rev]
            migration.applied = True
            applied.append(migration)
            if migration.down_revision:
                add_migration_and_ancestors(migration.down_revision)

        add_migration_and_ancestors(current_revision)

        # Sort by revision order (oldest first)
        applied.sort(key=lambda m: m.revision)

        return applied

    def get_pending_migrations(self) -> list[MigrationInfo]:
        """Get list of pending migrations.

        Returns:
            List of pending MigrationInfo objects
        """
        current_revision = self.get_current_revision()
        all_migrations = self._get_all_migration_files()

        if not current_revision:
            # No migrations applied, all are pending
            return all_migrations

        # Build chain from heads (handle multiple heads)
        revision_map = {m.revision: m for m in all_migrations}
        try:
            head_revisions = self.script_dir.get_heads()
        except Exception:
            # Fallback to get_current_head if get_heads fails
            head_revision = self.script_dir.get_current_head()
            head_revisions = [head_revision] if head_revision else []

        if not head_revisions:
            return []

        # Get applied revisions
        applied_migrations = self.get_applied_migrations()
        applied_revisions = {m.revision for m in applied_migrations}

        # Build chain from all heads to current, collecting pending
        pending = []
        visited = set()

        def collect_pending(rev: str):
            """Collect pending migrations from revision to current."""
            if rev in visited or rev not in revision_map:
                return
            visited.add(rev)

            migration = revision_map[rev]

            # If not applied, it's pending
            if migration.revision not in applied_revisions:
                pending.append(migration)

            # Stop if we've reached current revision
            if rev == current_revision:
                return

            # Continue to parent
            if migration.down_revision:
                collect_pending(migration.down_revision)

        # Start from all heads
        for head_revision in head_revisions:
            collect_pending(head_revision)

        # Reverse to get chronological order (oldest first)
        pending.reverse()

        return pending

    def get_status(self) -> MigrationStatus:
        """Get complete migration status.

        Returns:
            MigrationStatus object
        """
        current_revision = self.get_current_revision()
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()

        # Check for orphaned migrations (in DB but not in files)
        orphaned = []
        if current_revision:
            all_revisions = {m.revision for m in self._get_all_migration_files()}
            applied_revisions = {m.revision for m in applied}
            # Orphaned would be in applied but not in all_revisions
            orphaned = list(applied_revisions - all_revisions)

        return MigrationStatus(
            current_revision=current_revision,
            applied=applied,
            pending=pending,
            orphaned=orphaned,
        )

    def apply_migrations(self) -> MigrationResult:
        """Apply pending migrations.

        Returns:
            MigrationResult object
        """
        try:
            pending = self.get_pending_migrations()
            if not pending:
                return MigrationResult(
                    success=True,
                    applied_count=0,
                    warnings=["No pending migrations"],
                )

            # Capture output
            import io
            import sys

            old_stdout = sys.stdout
            sys.stdout = buffer = io.StringIO()

            try:
                # Use "heads" (plural) to handle multiple head revisions
                command.upgrade(self.alembic_cfg, "heads")
                buffer.getvalue()
            finally:
                sys.stdout = old_stdout

            applied_revisions = [m.revision for m in pending]

            return MigrationResult(
                success=True,
                applied_count=len(pending),
                applied_migrations=applied_revisions,
            )
        except Exception as e:
            return MigrationResult(
                success=False,
                errors=[str(e)],
            )

    def rollback(self, steps: int = 1) -> MigrationResult:
        """Rollback migrations.

        Args:
            steps: Number of migrations to rollback

        Returns:
            MigrationResult object
        """
        try:
            current_revision = self.get_current_revision()
            if not current_revision:
                return MigrationResult(
                    success=False,
                    errors=["No migrations to rollback"],
                )

            # Get target revision
            applied = self.get_applied_migrations()
            if len(applied) < steps:
                return MigrationResult(
                    success=False,
                    errors=[f"Only {len(applied)} migrations applied, cannot rollback {steps}"],
                )

            target_revision = applied[-(steps + 1)].revision if len(applied) > steps else None

            import io
            import sys

            old_stdout = sys.stdout
            sys.stdout = buffer = io.StringIO()

            try:
                if target_revision:
                    command.downgrade(self.alembic_cfg, target_revision)
                else:
                    command.downgrade(self.alembic_cfg, "base")
                buffer.getvalue()
            finally:
                sys.stdout = old_stdout

            return MigrationResult(
                success=True,
                applied_count=-steps,  # Negative to indicate rollback
            )
        except Exception as e:
            return MigrationResult(
                success=False,
                errors=[str(e)],
            )

    def fresh(self) -> MigrationResult:
        """Drop all tables and re-run migrations.

        Returns:
            MigrationResult object
        """
        try:
            # Drop all tables using SQL to ensure everything is removed
            with self.engine.begin() as connection:
                # Get all table names in public schema
                result = connection.execute(text("""
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                """))
                tables = [row[0] for row in result]

                # Drop all tables with CASCADE in a single transaction
                if tables:
                    # Build DROP statements
                    drop_statements = ', '.join([f'"{table}"' for table in tables])
                    connection.execute(text(f'DROP TABLE IF EXISTS {drop_statements} CASCADE'))

            # Run migrations from the beginning
            return self.apply_migrations()
        except Exception as e:
            return MigrationResult(
                success=False,
                errors=[str(e)],
            )

    def refresh(self) -> MigrationResult:
        """Rollback all migrations and re-run them.

        Returns:
            MigrationResult object
        """
        try:
            # Rollback all
            rollback_result = self.rollback(steps=999)  # Rollback all
            if not rollback_result.success:
                return rollback_result

            # Apply all
            return self.apply_migrations()
        except Exception as e:
            return MigrationResult(
                success=False,
                errors=[str(e)],
            )

    def create_migration(self, message: str, autogenerate: bool = True) -> str:
        """Create a new migration.

        Args:
            message: Migration description
            autogenerate: Whether to autogenerate from models

        Returns:
            Path to created migration file
        """
        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()

        try:
            if autogenerate:
                command.revision(self.alembic_cfg, message=message, autogenerate=True)
            else:
                command.revision(self.alembic_cfg, message=message)

            output = buffer.getvalue()
            # Extract file path from output
            # Alembic outputs: "Generating migrations/versions/..."
            match = re.search(r"Generating\s+([^\s]+)", output)
            if match:
                return match.group(1)
            return "Migration created"
        finally:
            sys.stdout = old_stdout

