"""REPL interactive shell commands."""

import sys
from pathlib import Path

import typer
from rich.console import Console

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

app = typer.Typer(help="REPL interactive shell")
console = Console()


@app.command()
def start() -> None:
    """Start IPython REPL with app context loaded."""
    try:
        from IPython import embed

        from app.core.config import get_settings

        # Import app context
        from app.core.db.session import SessionLocal, engine
        from app.models import (
            Base,
            Contact,
            ContactMethod,
            Organization,
            PersonIdentification,
            RefreshToken,
            SeederRecord,
            Tenant,
            User,
            UserRole,
        )

        settings = get_settings()
        db = SessionLocal()

        # Prepare namespace with common imports
        namespace = {
            "db": db,
            "engine": engine,
            "settings": settings,
            "Base": Base,
            "User": User,
            "Tenant": Tenant,
            "Organization": Organization,
            "Contact": Contact,
            "ContactMethod": ContactMethod,
            "UserRole": UserRole,
            "RefreshToken": RefreshToken,
            "PersonIdentification": PersonIdentification,
            "SeederRecord": SeederRecord,
            "SessionLocal": SessionLocal,
        }

        console.print("\n[bold cyan]Starting IPython REPL with AiutoX ERP context...[/bold cyan]")
        console.print("[dim]Available objects: db, engine, settings, models (User, Tenant, etc.)[/dim]")
        console.print("[dim]Type 'exit' or press Ctrl+D to quit[/dim]\n")

        # Start IPython with custom namespace
        embed(user_ns=namespace, colors="neutral")

    except ImportError:
        console.print("[red]✗ IPython is not installed[/red]")
        console.print("[yellow]Install it with: uv add --dev ipython[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error starting REPL: {e}[/red]")
        raise typer.Exit(1)

