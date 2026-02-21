"""Route listing commands."""

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app as fastapi_app

app = typer.Typer(help="Route listing commands")
console = Console()


@app.command()
def list() -> None:
    """List all API routes."""
    table = Table(title="API Routes", show_header=True, header_style="bold cyan")
    table.add_column("Method", style="cyan", no_wrap=True)
    table.add_column("Path", style="green")
    table.add_column("Name", style="yellow")
    table.add_column("Tags", style="blue")

    routes = []
    for route in fastapi_app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            # FastAPI route
            methods = ", ".join(sorted(route.methods - {"HEAD", "OPTIONS"}))
            path = route.path
            name = route.name if hasattr(route, "name") else "-"
            tags = (
                ", ".join(route.tags) if hasattr(route, "tags") and route.tags else "-"
            )
            routes.append((methods, path, name, tags))

    # Sort by path
    routes.sort(key=lambda x: x[1])

    for method, path, name, tags in routes:
        table.add_row(method, path, name, tags)

    if routes:
        console.print(f"\nFound {len(routes)} route(s):\n")
        console.print(table)
    else:
        console.print("[yellow]No routes found[/yellow]")
