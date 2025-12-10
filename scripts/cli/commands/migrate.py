"""Migration management commands."""

import sys
from pathlib import Path

import typer
from rich.console import Console

# Add backend to path for imports
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.migrations import MigrationManager, MigrationReporter, MigrationVerifier

# Import handlers from migrate_cli
# Note: migrate_cli.py also modifies sys.path, but that's OK
from scripts.migrate_cli import (
    handle_fresh,
    handle_history,
    handle_make_migration,
    handle_migrate,
    handle_refresh,
    handle_rollback,
    handle_seed,
    handle_status,
    handle_verify,
    interactive_mode,
    show_menu,
)

app = typer.Typer(help="Migration management commands")
console = Console()


def _get_managers() -> tuple[MigrationManager, MigrationVerifier, MigrationReporter]:
    """Get initialized migration managers.

    Returns:
        Tuple of (manager, verifier, reporter)
    """
    manager = MigrationManager()
    verifier = MigrationVerifier(manager)
    reporter = MigrationReporter()
    return manager, verifier, reporter


@app.command()
def apply() -> None:
    """Apply pending migrations."""
    manager, _, reporter = _get_managers()
    handle_migrate(manager, reporter)


@app.command()
def status() -> None:
    """Show migration status."""
    manager, _, reporter = _get_managers()
    handle_status(manager, reporter)


@app.command()
def verify() -> None:
    """Verify database vs migration files."""
    manager, verifier, reporter = _get_managers()
    handle_verify(manager, verifier, reporter)


@app.command()
def rollback(
    steps: int = typer.Option(1, "--steps", "-s", help="Number of migrations to rollback"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Rollback migrations.

    This will revert the last N migrations. Use with caution as this may cause data loss.
    """
    manager, _, reporter = _get_managers()
    status_obj = manager.get_status()

    if not status_obj.applied:
        console.print("[yellow]No migrations to rollback[/yellow]")
        raise typer.Exit(0)

    # Show migrations that will be rolled back
    migrations_to_rollback = status_obj.applied[-steps:]
    console.print("\n[bold yellow]⚠ WARNING: This will rollback the following migrations:[/bold yellow]")
    for i, migration in enumerate(migrations_to_rollback, 1):
        console.print(f"  {i}. {migration.revision} - {migration.file}")

    # Ask for confirmation unless --yes flag
    if not yes:
        console.print("\n[red]This action may cause data loss![/red]")
        confirm = typer.confirm("Are you sure you want to rollback these migrations?", default=False)
        if not confirm:
            console.print("[yellow]Rollback cancelled[/yellow]")
            raise typer.Exit(0)

    # Perform rollback
    console.print(f"\n[bold cyan]Rolling back {steps} migration(s)...[/bold cyan]")
    result = manager.rollback(steps=steps)

    if result.success:
        report = reporter.format_migration_result(result)
        console.print(f"\n{report}")
    else:
        console.print(f"\n[red]✗ Rollback failed:[/red]")
        for error in result.errors:
            console.print(f"  • {error}")
        raise typer.Exit(1)


@app.command()
def fresh(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Drop all tables and re-migrate."""
    if not yes:
        console.print("[red]Error: --yes flag required for fresh command[/red]")
        raise typer.Exit(1)

    manager, _, reporter = _get_managers()
    result = manager.fresh()
    report = reporter.format_migration_result(result)
    console.print(report)


@app.command()
def refresh(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Rollback all and re-migrate."""
    if not yes:
        console.print("[red]Error: --yes flag required for refresh command[/red]")
        raise typer.Exit(1)

    manager, _, reporter = _get_managers()
    result = manager.refresh()
    report = reporter.format_migration_result(result)
    console.print(report)


@app.command()
def make(
    name: str = typer.Argument(..., help="Migration description"),
    no_autogenerate: bool = typer.Option(False, "--no-autogenerate", help="Don't autogenerate from models"),
) -> None:
    """Create new migration."""
    manager, _, reporter = _get_managers()
    autogenerate = not no_autogenerate
    try:
        file_path = manager.create_migration(name, autogenerate=autogenerate)
        console.print(f"[green]✓ Migration created: {file_path}[/green]")
    except Exception as e:
        console.print(f"[red]✗ Error creating migration: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def history() -> None:
    """Show migration history."""
    manager, _, reporter = _get_managers()
    handle_history(manager, reporter)


@app.command()
def interactive() -> None:
    """Run interactive migration menu."""
    interactive_mode()

