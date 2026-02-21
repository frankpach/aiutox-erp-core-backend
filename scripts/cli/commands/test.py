"""Testing commands."""

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

app = typer.Typer(help="Testing commands")
console = Console()


def _run_command(cmd: list[str]) -> int:
    """Run command using uv run if available, otherwise direct execution.

    Args:
        cmd: Command to run

    Returns:
        Exit code
    """
    # Check if uv is available
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
        # Use uv run
        full_cmd = ["uv", "run"] + cmd
    except (FileNotFoundError, subprocess.CalledProcessError):
        # Fallback to direct execution
        full_cmd = cmd

    result = subprocess.run(full_cmd, cwd=backend_dir)
    return result.returncode


@app.command()
def run(
    coverage: bool = typer.Option(
        False, "--coverage", "-c", help="Generate coverage report"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Run tests."""
    cmd = ["pytest"]
    if verbose:
        cmd.append("-v")
    if coverage:
        cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term"])

    console.print("\n[bold cyan]Running tests...[/bold cyan]")
    exit_code = _run_command(cmd)
    if exit_code != 0:
        raise typer.Exit(exit_code)


@app.command()
def watch() -> None:
    """Run tests in watch mode."""
    console.print("\n[bold cyan]Running tests in watch mode...[/bold cyan]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    exit_code = _run_command(["pytest-watch"])
    if exit_code != 0:
        raise typer.Exit(exit_code)


@app.command()
def coverage() -> None:
    """Generate coverage report."""
    console.print("\n[bold cyan]Generating coverage report...[/bold cyan]")
    exit_code = _run_command(
        ["pytest", "--cov=app", "--cov-report=html", "--cov-report=term"]
    )
    if exit_code != 0:
        raise typer.Exit(exit_code)
