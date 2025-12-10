"""Database management commands."""

import sys
from pathlib import Path

import typer
from rich.console import Console
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.db.session import engine
from app.core.seeders import SeederManager

app = typer.Typer(help="Database management commands")
console = Console()


@app.command()
def seed(
    class_name: str = typer.Option(None, "--class", "-c", help="Run specific seeder class"),
) -> None:
    """Run database seeders."""
    from app.core.db.session import SessionLocal

    manager = SeederManager()
    db = SessionLocal()

    try:
        if class_name:
            # Run specific seeder
            console.print(f"\n[bold cyan]Running seeder: {class_name}[/bold cyan]")
            result = manager.run_seeder(class_name, db)
            if result["success"]:
                console.print(f"[green]✓ Seeder '{class_name}' executed successfully[/green]")
            else:
                console.print(f"[red]✗ Error: {result.get('error', 'Unknown error')}[/red]")
                raise typer.Exit(1)
        else:
            # Run all pending seeders
            console.print("\n[bold cyan]Running all pending seeders...[/bold cyan]")
            pending = manager.get_pending_seeders(db)
            if not pending:
                console.print("[yellow]No pending seeders[/yellow]")
                return

            console.print(f"\n[yellow]Pending seeders ({len(pending)}):[/yellow]")
            for seeder_class in pending:
                console.print(f"  • {seeder_class.__name__}")

            result = manager.run_all(db)
            if result["success"]:
                console.print(f"\n[green]✓ Executed {result['total']} seeder(s) successfully[/green]")
                for seeder_name in result["executed"]:
                    console.print(f"  • {seeder_name}")
            else:
                console.print(f"\n[red]✗ Error executing seeders:[/red]")
                console.print(f"  {result.get('error', 'Unknown error')}")
                if result.get("executed"):
                    console.print(f"\n[yellow]Partially executed ({len(result['executed'])} seeder(s)):[/yellow]")
                    for seeder_name in result["executed"]:
                        console.print(f"  • {seeder_name}")
                raise typer.Exit(1)
    finally:
        db.close()


@app.command()
def reset(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Reset database (fresh migrations + seed)."""
    from app.core.db.session import SessionLocal
    from app.core.migrations import MigrationManager, MigrationReporter

    console.print("\n[bold red]⚠ WARNING: This will drop ALL tables and re-migrate![/bold red]")

    if not yes:
        confirm = typer.confirm("Are you sure you want to reset the database?", default=False)
        if not confirm:
            console.print("[yellow]Reset cancelled[/yellow]")
            raise typer.Exit(0)

    # Run fresh migrations
    console.print("\n[bold cyan]Dropping all tables and re-migrating...[/bold cyan]")
    manager = MigrationManager()
    reporter = MigrationReporter()
    result = manager.fresh()
    report = reporter.format_migration_result(result)
    console.print(f"\n{report}")

    if not result.success:
        console.print("[red]✗ Migration failed, aborting seed[/red]")
        raise typer.Exit(1)

    # Run seeders
    console.print("\n[bold cyan]Running seeders...[/bold cyan]")
    seeder_manager = SeederManager()
    seed_db = SessionLocal()

    try:
        seed_result = seeder_manager.run_all(seed_db)
        if seed_result["success"]:
            console.print(f"[green]✓ Executed {seed_result['total']} seeder(s) successfully[/green]")
            for seeder_name in seed_result["executed"]:
                console.print(f"  • {seeder_name}")
        else:
            console.print(f"[yellow]⚠ Seeders completed with warnings[/yellow]")
    finally:
        seed_db.close()

    console.print("\n[green]✓ Database reset completed[/green]")


@app.command()
def seed_rollback() -> None:
    """Rollback last executed seeder."""
    from app.core.db.session import SessionLocal

    manager = SeederManager()
    db = SessionLocal()

    try:
        console.print("\n[bold cyan]Rolling back last seeder...[/bold cyan]")
        result = manager.rollback_last(db)
        if result["success"]:
            console.print(f"[green]✓ Rolled back seeder: {result['rolled_back']}[/green]")
        else:
            console.print(f"[red]✗ Error: {result.get('error', 'Unknown error')}[/red]")
            raise typer.Exit(1)
    finally:
        db.close()


@app.command()
def check() -> None:
    """Check database connection and status."""
    console.print("\n[bold cyan]Checking database connection...[/bold cyan]")

    try:
        with engine.connect() as connection:
            # Test connection
            result = connection.execute(text("SELECT version()"))
            version = result.scalar()

            # Get database name
            result = connection.execute(text("SELECT current_database()"))
            db_name = result.scalar()

            # Get table count
            result = connection.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
            table_count = result.scalar()

            console.print("\n[green]✓ Database connection successful[/green]")
            console.print(f"\n[bold]Database Information:[/bold]")
            console.print(f"  Name: {db_name}")
            console.print(f"  Version: {version.split(',')[0]}")
            console.print(f"  Tables: {table_count}")

    except SQLAlchemyError as e:
        console.print(f"\n[red]✗ Database connection failed:[/red]")
        console.print(f"  {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]✗ Unexpected error:[/red]")
        console.print(f"  {e}")
        raise typer.Exit(1)

