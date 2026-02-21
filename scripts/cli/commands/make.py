"""Code generation commands."""

import typer
from rich.console import Console

from scripts.cli.utils.generators import (
    generate_model,
    generate_module,
    generate_repository,
    generate_router,
    generate_schema,
    generate_seeder,
    generate_service,
)

app = typer.Typer(help="Code generation commands")
console = Console()


@app.command()
def model(
    name: str = typer.Argument(..., help="Model name (e.g., User, Product)")
) -> None:
    """Generate SQLAlchemy model."""
    try:
        generate_model(name)
    except FileExistsError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error generating model: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def service(
    name: str = typer.Argument(..., help="Service name (e.g., User, Product)")
) -> None:
    """Generate service."""
    try:
        generate_service(name)
    except FileExistsError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error generating service: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def repository(
    name: str = typer.Argument(..., help="Repository name (e.g., User, Product)")
) -> None:
    """Generate repository."""
    try:
        generate_repository(name)
    except FileExistsError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error generating repository: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def router(
    name: str = typer.Argument(..., help="Router name (e.g., User, Product)")
) -> None:
    """Generate FastAPI router."""
    try:
        generate_router(name)
    except FileExistsError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error generating router: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def schema(
    name: str = typer.Argument(..., help="Schema name (e.g., User, Product)")
) -> None:
    """Generate Pydantic schema."""
    try:
        generate_schema(name)
    except FileExistsError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error generating schema: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def module(
    name: str = typer.Argument(..., help="Module name (e.g., Product, Order)"),
    entities: str = typer.Option(
        "", "--entities", help="Comma-separated list of entities (default: module name)"
    ),
) -> None:
    """Generate complete module (model, schema, repository, service, router)."""
    try:
        entity_list = [e.strip() for e in entities.split(",")] if entities else None
        generate_module(name, entity_list)
    except FileExistsError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error generating module: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def seeder(
    name: str = typer.Argument(..., help="Seeder name (e.g., User, Database, Product)")
) -> None:
    """Generate database seeder."""
    try:
        generate_seeder(name)
    except FileExistsError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error generating seeder: {e}[/red]")
        raise typer.Exit(1)
