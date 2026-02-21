#!/usr/bin/env python3
"""Interactive CLI for managing Alembic migrations."""

import argparse
import sys
from pathlib import Path

import inquirer
from rich.console import Console
from rich.panel import Panel

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.migrations import MigrationManager, MigrationReporter, MigrationVerifier

console = Console()


def show_menu() -> str:
    """Show interactive menu and return selected option.

    Returns:
        Selected menu option
    """
    console.print(
        Panel.fit(
            "[bold cyan]AiutoX ERP - Migration Manager (Interactive)[/bold cyan]",
            border_style="cyan",
        )
    )

    questions = [
        inquirer.List(
            "action",
            message="Select an action",
            choices=[
                ("Migrate - Apply pending migrations", "migrate"),
                ("Status - View current status", "status"),
                ("Verify - Verify database vs files", "verify"),
                ("Rollback - Revert last migration", "rollback"),
                ("Fresh - Drop all tables and migrate", "fresh"),
                ("Refresh - Rollback all and migrate", "refresh"),
                ("Make Migration - Create new migration", "make_migration"),
                ("Seed Database - Run database seeds", "seed"),
                ("Show History - View migration history", "history"),
                ("Exit", "exit"),
            ],
        ),
    ]

    answers = inquirer.prompt(questions)
    return answers["action"] if answers else "exit"


def handle_migrate(manager: MigrationManager, reporter: MigrationReporter) -> None:
    """Handle migrate command."""
    console.print("\n[bold cyan]Applying Migrations...[/bold cyan]")

    # Show pending migrations
    status = manager.get_status()
    if status.pending:
        console.print(f"\n[yellow]Pending migrations ({len(status.pending)}):[/yellow]")
        for migration in status.pending:
            console.print(f"  ÔÇó {migration.revision} - {migration.file}")

        # Confirm
        questions = [
            inquirer.Confirm("confirm", message="Apply these migrations?", default=True),
        ]
        answers = inquirer.prompt(questions)
        if not answers or not answers.get("confirm"):
            console.print("[yellow]Cancelled[/yellow]")
            return
    else:
        console.print("[green]No pending migrations[/green]")
        return

    # Apply migrations
    result = manager.apply_migrations()
    report = reporter.format_migration_result(result)
    console.print(f"\n{report}")


def handle_status(manager: MigrationManager, reporter: MigrationReporter) -> None:
    """Handle status command."""
    console.print("\n[bold cyan]Migration Status[/bold cyan]")
    status = manager.get_status()
    report = reporter.generate_status_report(status)
    console.print(f"\n{report}")


def handle_verify(manager: MigrationManager, verifier: MigrationVerifier, reporter: MigrationReporter) -> None:
    """Handle verify command."""
    console.print("\n[bold cyan]Verifying Migrations...[/bold cyan]")
    result = verifier.verify_all()
    report = reporter.generate_verification_report(result)
    console.print(f"\n{report}")


def handle_rollback(manager: MigrationManager, reporter: MigrationReporter) -> None:
    """Handle rollback command."""
    console.print("\n[bold cyan]Rollback Migration[/bold cyan]")

    # Show applied migrations
    status = manager.get_status()
    if not status.applied:
        console.print("[yellow]No migrations to rollback[/yellow]")
        return

    console.print(f"\n[yellow]Applied migrations ({len(status.applied)}):[/yellow]")
    for i, migration in enumerate(status.applied[-5:], 1):  # Show last 5
        console.print(f"  {i}. {migration.revision} - {migration.file}")

    # Ask for steps
    questions = [
        inquirer.Text(
            "steps",
            message="How many migrations to rollback?",
            default="1",
            validate=lambda _, x: x.isdigit() and int(x) > 0,
        ),
        inquirer.Confirm("confirm", message="Confirm rollback?", default=False),
    ]
    answers = inquirer.prompt(questions)
    if not answers or not answers.get("confirm"):
        console.print("[yellow]Cancelled[/yellow]")
        return

    steps = int(answers["steps"])
    result = manager.rollback(steps=steps)
    report = reporter.format_migration_result(result)
    console.print(f"\n{report}")


def handle_fresh(manager: MigrationManager, reporter: MigrationReporter) -> None:
    """Handle fresh command."""
    console.print("\n[bold red]ÔÜá WARNING: This will drop ALL tables![/bold red]")
    questions = [
        inquirer.Confirm(
            "confirm",
            message="Are you sure you want to drop all tables and re-migrate?",
            default=False,
        ),
    ]
    answers = inquirer.prompt(questions)
    if not answers or not answers.get("confirm"):
        console.print("[yellow]Cancelled[/yellow]")
        return

    console.print("\n[bold cyan]Dropping all tables and re-migrating...[/bold cyan]")
    result = manager.fresh()
    report = reporter.format_migration_result(result)
    console.print(f"\n{report}")


def handle_refresh(manager: MigrationManager, reporter: MigrationReporter) -> None:
    """Handle refresh command."""
    console.print("\n[bold yellow]ÔÜá This will rollback all migrations and re-apply them[/bold yellow]")
    questions = [
        inquirer.Confirm(
            "confirm",
            message="Rollback all migrations and re-apply?",
            default=False,
        ),
    ]
    answers = inquirer.prompt(questions)
    if not answers or not answers.get("confirm"):
        console.print("[yellow]Cancelled[/yellow]")
        return

    console.print("\n[bold cyan]Refreshing migrations...[/bold cyan]")
    result = manager.refresh()
    report = reporter.format_migration_result(result)
    console.print(f"\n{report}")


def handle_make_migration(manager: MigrationManager, reporter: MigrationReporter) -> None:
    """Handle make migration command."""
    console.print("\n[bold cyan]Create New Migration[/bold cyan]")
    questions = [
        inquirer.Text("message", message="Migration description", validate=lambda _, x: len(x) > 0),
        inquirer.Confirm("autogenerate", message="Autogenerate from models?", default=True),
    ]
    answers = inquirer.prompt(questions)
    if not answers:
        console.print("[yellow]Cancelled[/yellow]")
        return

    message = answers["message"]
    autogenerate = answers.get("autogenerate", True)

    console.print("\n[bold cyan]Creating migration...[/bold cyan]")
    try:
        file_path = manager.create_migration(message, autogenerate=autogenerate)
        console.print(f"[green]Ô£ô Migration created: {file_path}[/green]")
    except Exception as e:
        console.print(f"[red]Ô£ù Error creating migration: {e}[/red]")


def handle_seed(manager: MigrationManager, reporter: MigrationReporter) -> None:
    """Handle seed command."""
    console.print("\n[yellow]Seed functionality not yet implemented[/yellow]")
    console.print("This will be available in a future update")


def handle_history(manager: MigrationManager, reporter: MigrationReporter) -> None:
    """Handle history command."""
    console.print("\n[bold cyan]Migration History[/bold cyan]")
    status = manager.get_status()

    all_migrations = manager._get_all_migration_files()
    console.print(f"\nTotal migrations: {len(all_migrations)}")
    console.print(f"Applied: {len(status.applied)}")
    console.print(f"Pending: {len(status.pending)}")

    if all_migrations:
        table = reporter.format_migration_list(all_migrations)
        console.print(f"\n{table}")


def interactive_mode() -> None:
    """Run in interactive mode."""
    manager = MigrationManager()
    verifier = MigrationVerifier(manager)
    reporter = MigrationReporter()

    while True:
        try:
            action = show_menu()

            if action == "exit":
                console.print("\n[cyan]Goodbye![/cyan]")
                break
            elif action == "migrate":
                handle_migrate(manager, reporter)
            elif action == "status":
                handle_status(manager, reporter)
            elif action == "verify":
                handle_verify(manager, verifier, reporter)
            elif action == "rollback":
                handle_rollback(manager, reporter)
            elif action == "fresh":
                handle_fresh(manager, reporter)
            elif action == "refresh":
                handle_refresh(manager, reporter)
            elif action == "make_migration":
                handle_make_migration(manager, reporter)
            elif action == "seed":
                handle_seed(manager, reporter)
            elif action == "history":
                handle_history(manager, reporter)

            if action != "exit":
                console.print("\n[dim]Press Enter to continue...[/dim]")
                input()

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted by user[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            import traceback

            traceback.print_exc()


def non_interactive_mode(args: argparse.Namespace) -> None:
    """Run in non-interactive mode."""
    manager = MigrationManager()
    verifier = MigrationVerifier(manager)
    reporter = MigrationReporter()

    try:
        if args.command == "migrate":
            handle_migrate(manager, reporter)
        elif args.command == "status":
            handle_status(manager, reporter)
        elif args.command == "verify":
            handle_verify(manager, verifier, reporter)
        elif args.command == "rollback":
            steps = getattr(args, "steps", 1)
            result = manager.rollback(steps=steps)
            report = reporter.format_migration_result(result)
            console.print(report)
        elif args.command == "fresh":
            if not args.yes:
                console.print("[red]Error: --yes flag required for fresh command[/red]")
                sys.exit(1)
            result = manager.fresh()
            report = reporter.format_migration_result(result)
            console.print(report)
        elif args.command == "refresh":
            if not args.yes:
                console.print("[red]Error: --yes flag required for refresh command[/red]")
                sys.exit(1)
            result = manager.refresh()
            report = reporter.format_migration_result(result)
            console.print(report)
        elif args.command == "make:migration":
            message = args.name
            autogenerate = not args.no_autogenerate
            file_path = manager.create_migration(message, autogenerate=autogenerate)
            console.print(f"[green]Ô£ô Migration created: {file_path}[/green]")
        elif args.command == "seed":
            handle_seed(manager, reporter)
        else:
            console.print(f"[red]Unknown command: {args.command}[/red]")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive CLI for managing Alembic migrations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Migrate command
    subparsers.add_parser("migrate", help="Apply pending migrations")

    # Status command
    subparsers.add_parser("status", help="View migration status")

    # Verify command
    subparsers.add_parser("verify", help="Verify database vs migration files")

    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Revert migrations")
    rollback_parser.add_argument(
        "--steps",
        type=int,
        default=1,
        help="Number of migrations to rollback (default: 1)",
    )

    # Fresh command
    fresh_parser = subparsers.add_parser("fresh", help="Drop all tables and re-migrate")
    fresh_parser.add_argument("--yes", action="store_true", help="Skip confirmation")

    # Refresh command
    refresh_parser = subparsers.add_parser("refresh", help="Rollback all and re-migrate")
    refresh_parser.add_argument("--yes", action="store_true", help="Skip confirmation")

    # Make migration command
    make_parser = subparsers.add_parser("make:migration", help="Create new migration")
    make_parser.add_argument("name", help="Migration description")
    make_parser.add_argument(
        "--no-autogenerate",
        action="store_true",
        help="Don't autogenerate from models",
    )

    # Seed command
    subparsers.add_parser("seed", help="Run database seeds")

    # If no arguments, run interactive mode
    if len(sys.argv) == 1:
        interactive_mode()
    else:
        args = parser.parse_args()
        if not args.command:
            parser.print_help()
            sys.exit(1)
        non_interactive_mode(args)


if __name__ == "__main__":
    main()


