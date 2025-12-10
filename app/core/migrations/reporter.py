"""Migration reporter for generating formatted reports."""

from datetime import datetime
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from tabulate import tabulate

from app.core.migrations.models import (
    MigrationInfo,
    MigrationResult,
    MigrationStatus,
    SchemaDiff,
    VerificationResult,
)

console = Console()


class MigrationReporter:
    """Reporter for generating formatted migration reports."""

    def __init__(self):
        """Initialize migration reporter."""
        self.console = console

    def generate_status_report(self, status: MigrationStatus) -> str:
        """Generate status report.

        Args:
            status: MigrationStatus object

        Returns:
            Formatted status report string
        """
        output = []

        # Header
        self.console.print(
            Panel.fit(
                "[bold cyan]Migration Status Report[/bold cyan]",
                border_style="cyan",
            )
        )

        # Current revision
        current = status.current_revision or "None (no migrations applied)"
        self.console.print(f"\n[bold]Current Revision:[/bold] {current}")

        # Applied migrations
        if status.applied:
            table = Table(title="Applied Migrations", show_header=True, header_style="bold green")
            table.add_column("Revision", style="cyan")
            table.add_column("File", style="white")
            table.add_column("Description", style="dim")

            for migration in status.applied:
                desc = migration.description or "No description"
                if len(desc) > 50:
                    desc = desc[:47] + "..."
                table.add_row(migration.revision, migration.file, desc)

            self.console.print(f"\n[green]✓ Applied Migrations ({len(status.applied)}):[/green]")
            self.console.print(table)
        else:
            self.console.print("\n[yellow]⚠ No migrations applied[/yellow]")

        # Pending migrations
        if status.pending:
            table = Table(title="Pending Migrations", show_header=True, header_style="bold yellow")
            table.add_column("Revision", style="cyan")
            table.add_column("File", style="white")
            table.add_column("Description", style="dim")

            for migration in status.pending:
                desc = migration.description or "No description"
                if len(desc) > 50:
                    desc = desc[:47] + "..."
                table.add_row(migration.revision, migration.file, desc)

            self.console.print(f"\n[yellow]⏳ Pending Migrations ({len(status.pending)}):[/yellow]")
            self.console.print(table)
        else:
            self.console.print("\n[green]✓ No pending migrations[/green]")

        # Orphaned migrations
        if status.orphaned:
            self.console.print(f"\n[red]⚠ Orphaned Migrations ({len(status.orphaned)}):[/red]")
            for orphaned in status.orphaned:
                self.console.print(f"  • {orphaned}")
        else:
            self.console.print("\n[green]✓ No orphaned migrations[/green]")

        # Capture output
        # Note: Rich doesn't easily return strings, so we'll use a different approach
        # For now, return a simple text representation
        return self._status_to_text(status)

    def _status_to_text(self, status: MigrationStatus) -> str:
        """Convert status to text representation."""
        lines = []
        lines.append("=" * 60)
        lines.append("Migration Status Report")
        lines.append("=" * 60)
        lines.append(f"\nCurrent Revision: {status.current_revision or 'None'}")
        lines.append(f"\nApplied Migrations ({len(status.applied)}):")
        for migration in status.applied:
            desc = migration.description or "No description"
            lines.append(f"  ✓ {migration.revision} - {migration.file}")
            if desc:
                lines.append(f"    {desc}")

        lines.append(f"\nPending Migrations ({len(status.pending)}):")
        for migration in status.pending:
            desc = migration.description or "No description"
            lines.append(f"  ⏳ {migration.revision} - {migration.file}")
            if desc:
                lines.append(f"    {desc}")

        if status.orphaned:
            lines.append(f"\nOrphaned Migrations ({len(status.orphaned)}):")
            for orphaned in status.orphaned:
                lines.append(f"  ⚠ {orphaned}")

        return "\n".join(lines)

    def generate_verification_report(self, result: VerificationResult) -> str:
        """Generate verification report.

        Args:
            result: VerificationResult object

        Returns:
            Formatted verification report string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("Migration Verification Report")
        lines.append("=" * 60)

        # Applied match
        status_icon = "✓" if result.applied_match else "✗"
        status_text = "OK" if result.applied_match else "FAILED"
        lines.append(f"\nApplied Migrations Match: {status_icon} {status_text}")

        # Schema match
        status_icon = "✓" if result.schema_match else "✗"
        status_text = "OK" if result.schema_match else "FAILED"
        lines.append(f"Schema Match: {status_icon} {status_text}")

        # Integrity
        status_icon = "✓" if result.integrity_ok else "✗"
        status_text = "OK" if result.integrity_ok else "FAILED"
        lines.append(f"Integrity Check: {status_icon} {status_text}")

        # Issues
        if result.issues:
            lines.append(f"\nIssues Found ({len(result.issues)}):")
            for issue in result.issues:
                lines.append(f"  • {issue}")
        else:
            lines.append("\n✓ No issues found")

        # Schema diff
        if result.schema_diff:
            diff = result.schema_diff
            if diff.missing_tables:
                lines.append(f"\nMissing Tables ({len(diff.missing_tables)}):")
                for table in diff.missing_tables:
                    lines.append(f"  • {table}")

            if diff.extra_tables:
                lines.append(f"\nExtra Tables ({len(diff.extra_tables)}):")
                for table in diff.extra_tables:
                    lines.append(f"  • {table}")

            if diff.missing_columns:
                lines.append(f"\nMissing Columns ({len(diff.missing_columns)}):")
                for table, column in diff.missing_columns:
                    lines.append(f"  • {table}.{column}")

            if diff.extra_columns:
                lines.append(f"\nExtra Columns ({len(diff.extra_columns)}):")
                for table, column in diff.extra_columns:
                    lines.append(f"  • {table}.{column}")

            if diff.column_type_mismatches:
                lines.append(f"\nType Mismatches ({len(diff.column_type_mismatches)}):")
                for table, column, expected, actual in diff.column_type_mismatches:
                    lines.append(f"  • {table}.{column}: expected {expected}, got {actual}")

        return "\n".join(lines)

    def format_migration_list(self, migrations: List[MigrationInfo]) -> str:
        """Format list of migrations.

        Args:
            migrations: List of MigrationInfo objects

        Returns:
            Formatted migration list
        """
        if not migrations:
            return "No migrations"

        table_data = []
        for migration in migrations:
            status = "✓" if migration.applied else "⏳"
            desc = migration.description or "No description"
            if len(desc) > 40:
                desc = desc[:37] + "..."
            table_data.append([status, migration.revision, migration.file, desc])

        return tabulate(
            table_data,
            headers=["Status", "Revision", "File", "Description"],
            tablefmt="grid",
        )

    def format_table_diff(self, diff: SchemaDiff) -> str:
        """Format schema differences.

        Args:
            diff: SchemaDiff object

        Returns:
            Formatted diff string
        """
        lines = []
        lines.append("Schema Differences:")
        lines.append("-" * 60)

        if diff.missing_tables:
            lines.append(f"\nMissing Tables ({len(diff.missing_tables)}):")
            for table in diff.missing_tables:
                lines.append(f"  • {table}")

        if diff.extra_tables:
            lines.append(f"\nExtra Tables ({len(diff.extra_tables)}):")
            for table in diff.extra_tables:
                lines.append(f"  • {table}")

        if diff.missing_columns:
            lines.append(f"\nMissing Columns ({len(diff.missing_columns)}):")
            for table, column in diff.missing_columns:
                lines.append(f"  • {table}.{column}")

        if diff.extra_columns:
            lines.append(f"\nExtra Columns ({len(diff.extra_columns)}):")
            for table, column in diff.extra_columns:
                lines.append(f"  • {table}.{column}")

        if diff.column_type_mismatches:
            lines.append(f"\nType Mismatches ({len(diff.column_type_mismatches)}):")
            for table, column, expected, actual in diff.column_type_mismatches:
                lines.append(f"  • {table}.{column}: {expected} → {actual}")

        if not any(
            [
                diff.missing_tables,
                diff.extra_tables,
                diff.missing_columns,
                diff.extra_columns,
                diff.column_type_mismatches,
            ]
        ):
            lines.append("\n✓ No differences found")

        return "\n".join(lines)

    def format_migration_result(self, result: MigrationResult) -> str:
        """Format migration operation result.

        Args:
            result: MigrationResult object

        Returns:
            Formatted result string
        """
        lines = []
        lines.append("=" * 60)
        if result.success:
            lines.append("✓ Migration Operation Successful")
        else:
            lines.append("✗ Migration Operation Failed")
        lines.append("=" * 60)

        if result.applied_count > 0:
            lines.append(f"\nApplied Migrations: {result.applied_count}")
            for migration in result.applied_migrations:
                lines.append(f"  • {migration}")
        elif result.applied_count < 0:
            lines.append(f"\nRolled Back Migrations: {abs(result.applied_count)}")

        if result.warnings:
            lines.append(f"\nWarnings ({len(result.warnings)}):")
            for warning in result.warnings:
                lines.append(f"  ⚠ {warning}")

        if result.errors:
            lines.append(f"\nErrors ({len(result.errors)}):")
            for error in result.errors:
                lines.append(f"  ✗ {error}")

        return "\n".join(lines)

    def print_status_report(self, status: MigrationStatus) -> None:
        """Print status report to console using Rich.

        Args:
            status: MigrationStatus object
        """
        self.generate_status_report(status)
        # Rich already prints, so we just call it

    def print_verification_report(self, result: VerificationResult) -> None:
        """Print verification report to console.

        Args:
            result: VerificationResult object
        """
        report = self.generate_verification_report(result)
        self.console.print(Panel(report, title="Verification Report", border_style="blue"))


