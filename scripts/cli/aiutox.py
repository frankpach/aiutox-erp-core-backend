"""Main CLI entry point for AiutoX ERP."""

import typer
from rich.console import Console

from scripts.cli.commands import analyze, db, make, migrate, repl, route, test

app = typer.Typer(
    name="aiutox",
    help="AiutoX ERP CLI - Unified development tools",
    add_completion=False,
)
console = Console()

# Register subcommands
app.add_typer(make.app, name="make")
app.add_typer(migrate.app, name="migrate")
app.add_typer(db.app, name="db")
app.add_typer(test.app, name="test")
app.add_typer(route.app, name="route")
app.add_typer(analyze.app, name="analyze")
app.add_typer(repl.app, name="repl")


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()

