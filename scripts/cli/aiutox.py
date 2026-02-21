"""Unified CLI entrypoint for backend tooling."""

from __future__ import annotations

import typer
from sqlalchemy import create_engine, text

from app.core.config_file import get_settings
from app.core.migrations.manager import MigrationManager
from app.core.migrations.reporter import MigrationReporter
from app.core.migrations.verifier import MigrationVerifier
from app.core.seeders.manager import SeederManager

app = typer.Typer(help="AiutoX unified backend CLI")
migrate_app = typer.Typer(help="Migration commands")
app.add_typer(migrate_app, name="migrate")


def _exit_with_error(message: str) -> None:
    typer.echo(message)
    raise typer.Exit(code=1)


@migrate_app.command("apply")
def migrate_apply() -> None:
    """Apply pending migrations."""
    result = MigrationManager().apply_migrations()
    if not result.success:
        _exit_with_error(f"Migration failed: {result.errors}")

    typer.echo(f"Migrations applied: {result.applied_count}")


@migrate_app.command("status")
def migrate_status() -> None:
    """Show migration status."""
    status = MigrationManager().get_status()
    typer.echo(f"Current revision: {status.current_revision}")
    typer.echo(f"Applied: {len(status.applied)}")
    typer.echo(f"Pending: {len(status.pending)}")
    typer.echo(f"Orphaned: {len(status.orphaned)}")


@migrate_app.command("verify")
def migrate_verify() -> None:
    """Verify migration state, schema and chain integrity."""
    verifier = MigrationVerifier()
    reporter = MigrationReporter()
    result = verifier.verify_all()
    typer.echo(reporter.generate_verification_report(result))

    if not (result.applied_match and result.schema_match and result.integrity_ok):
        raise typer.Exit(code=1)


@migrate_app.command("rollback")
def migrate_rollback(
    steps: int = typer.Option(1, "--steps", min=1),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt"),
) -> None:
    """Rollback applied migrations."""
    if not yes:
        confirmed = typer.confirm(
            f"Rollback {steps} migration(s)?",
            default=False,
        )
        if not confirmed:
            raise typer.Exit(code=0)

    result = MigrationManager().rollback(steps=steps)
    if not result.success:
        _exit_with_error(f"Rollback failed: {result.errors}")

    typer.echo(f"Rolled back migrations: {abs(result.applied_count)}")


@migrate_app.command("fresh")
def migrate_fresh(
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt"),
) -> None:
    """Drop all tables and run migrations from scratch."""
    if not yes:
        confirmed = typer.confirm(
            "This will drop all tables. Continue?",
            default=False,
        )
        if not confirmed:
            raise typer.Exit(code=0)

    result = MigrationManager().fresh()
    if not result.success:
        _exit_with_error(f"Fresh migration failed: {result.errors}")

    typer.echo(f"Fresh migration completed. Applied: {result.applied_count}")


@migrate_app.command("refresh")
def migrate_refresh(
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt"),
) -> None:
    """Rollback all migrations and apply again."""
    if not yes:
        confirmed = typer.confirm(
            "This will rollback and re-apply migrations. Continue?",
            default=False,
        )
        if not confirmed:
            raise typer.Exit(code=0)

    result = MigrationManager().refresh()
    if not result.success:
        _exit_with_error(f"Refresh migration failed: {result.errors}")

    typer.echo(f"Migration refresh completed. Applied: {result.applied_count}")


@migrate_app.command("make")
def migrate_make(
    message: str = typer.Argument(..., help="Migration description"),
    empty: bool = typer.Option(False, "--empty", help="Create empty migration"),
) -> None:
    """Create a new migration file."""
    migration_path = MigrationManager().create_migration(
        message=message,
        autogenerate=not empty,
    )
    typer.echo(f"Migration created: {migration_path}")


@migrate_app.command("history")
def migrate_history() -> None:
    """Show migration files history."""
    manager = MigrationManager()
    reporter = MigrationReporter()
    migrations = manager._get_all_migration_files()
    typer.echo(reporter.format_migration_list(migrations))


@migrate_app.command("interactive")
def migrate_interactive() -> None:
    """Run interactive migration menu."""
    menu = (
        "\nMigration menu:\n"
        "  1) status\n"
        "  2) apply\n"
        "  3) verify\n"
        "  4) rollback\n"
        "  5) fresh\n"
        "  6) refresh\n"
        "  7) make\n"
        "  8) history\n"
        "  0) exit\n"
    )

    while True:
        typer.echo(menu)
        choice = typer.prompt("Select an option", default="0").strip()

        if choice == "1":
            migrate_status()
        elif choice == "2":
            migrate_apply()
        elif choice == "3":
            migrate_verify()
        elif choice == "4":
            steps = int(typer.prompt("Rollback steps", default="1"))
            confirmed = typer.confirm(
                f"Rollback {steps} migration(s)?",
                default=False,
            )
            if confirmed:
                migrate_rollback(steps=steps, yes=True)
        elif choice == "5":
            if typer.confirm(
                "Drop all tables and run migrations from scratch?", default=False
            ):
                migrate_fresh(yes=True)
        elif choice == "6":
            if typer.confirm("Rollback all migrations and apply again?", default=False):
                migrate_refresh(yes=True)
        elif choice == "7":
            message = typer.prompt("Migration description").strip()
            empty = typer.confirm("Create empty migration?", default=False)
            migrate_make(message=message, empty=empty)
        elif choice == "8":
            migrate_history()
        elif choice == "0":
            typer.echo("Bye.")
            break
        else:
            typer.echo("Invalid option.")


@app.command("db:seed")
def db_seed(class_name: str | None = typer.Option(None, "--class")) -> None:
    """Run database seeders (all or specific class)."""
    manager = SeederManager()
    if class_name:
        result = manager.run_seeder(class_name)
    else:
        result = manager.run_all()

    if not result.get("success"):
        _exit_with_error(f"Seeding failed: {result}")

    typer.echo(f"Seeders executed: {result.get('executed', [])}")


@app.command("db:seed:rollback")
def db_seed_rollback() -> None:
    """Rollback last executed seeder record."""
    result = SeederManager().rollback_last()
    if not result.get("success"):
        _exit_with_error(f"Seeder rollback failed: {result}")

    typer.echo(f"Seeder rolled back: {result.get('rolled_back')}")


@app.command("db:check")
def db_check() -> None:
    """Check database and redis connectivity."""
    settings = get_settings()

    try:
        engine = create_engine(settings.database_url)
        connection = engine.connect()
        connection.execute(text("SELECT 1"))
        connection.close()
    except Exception as exc:  # pragma: no cover - connectivity depends on env
        _exit_with_error(f"Database check failed: {exc}")

    try:
        import redis

        redis.from_url(settings.REDIS_URL).ping()
    except Exception as exc:  # pragma: no cover - connectivity depends on env
        _exit_with_error(f"Redis check failed: {exc}")

    typer.echo("Database and Redis check: OK")


def main() -> None:
    """CLI entrypoint for `uv run aiutox`."""
    app()


if __name__ == "__main__":
    main()
