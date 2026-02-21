"""Code analysis commands."""

import sys
from pathlib import Path

import typer
from rich.console import Console

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

app = typer.Typer(help="Code analysis commands")
console = Console()


@app.command()
def complexity(
    path: str = typer.Option("app", "--path", "-p", help="Path to analyze"),
    min: str = typer.Option("B", "--min", help="Minimum complexity grade (A-F)"),
) -> None:
    """Analyze code complexity using radon."""
    try:
        import subprocess

        console.print(
            f"\n[bold cyan]Analyzing code complexity in '{path}'...[/bold cyan]"
        )
        result = subprocess.run(
            ["radon", "cc", path, "--min", min, "--show-complexity"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print(result.stdout)
        else:
            console.print(f"[red]✗ Error: {result.stderr}[/red]")
            raise typer.Exit(1)

    except FileNotFoundError:
        console.print("[red]✗ Radon is not installed[/red]")
        console.print("[yellow]Install it with: uv add --dev radon[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def security(
    path: str = typer.Option("app", "--path", "-p", help="Path to analyze"),
    level: int = typer.Option(1, "--level", "-l", help="Minimum severity level (1-3)"),
) -> None:
    """Analyze code security using bandit."""
    try:
        import subprocess

        console.print(
            f"\n[bold cyan]Analyzing code security in '{path}'...[/bold cyan]"
        )
        result = subprocess.run(
            ["bandit", "-r", path, "-l", str(level), "-f", "json"],
            capture_output=True,
            text=True,
        )

        # Bandit returns non-zero on findings, so we check stderr
        if result.returncode in (0, 1):
            # Try to parse JSON output
            import json

            try:
                data = json.loads(result.stdout)
                issues = data.get("results", [])

                if issues:
                    console.print(
                        f"\n[yellow]⚠ Found {len(issues)} security issue(s):[/yellow]\n"
                    )
                    for issue in issues:
                        severity = issue.get("issue_severity", "UNKNOWN")
                        confidence = issue.get("issue_confidence", "UNKNOWN")
                        test_name = issue.get("test_name", "Unknown")
                        filename = issue.get("filename", "Unknown")
                        line = issue.get("line_number", "?")

                        severity_color = {
                            "HIGH": "red",
                            "MEDIUM": "yellow",
                            "LOW": "blue",
                        }.get(severity, "white")

                        console.print(
                            f"[{severity_color}]{severity}[/{severity_color}] "
                            f"({confidence}) {test_name} in {filename}:{line}"
                        )
                else:
                    console.print("[green]✓ No security issues found[/green]")
            except json.JSONDecodeError:
                # Fallback to stdout if JSON parsing fails
                console.print(result.stdout)
        else:
            console.print(f"[red]✗ Error: {result.stderr}[/red]")
            raise typer.Exit(1)

    except FileNotFoundError:
        console.print("[red]✗ Bandit is not installed[/red]")
        console.print("[yellow]Install it with: uv add --dev bandit[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def dependencies() -> None:
    """Check dependencies for known security vulnerabilities using safety."""
    try:
        import subprocess

        console.print(
            "\n[bold cyan]Checking dependencies for vulnerabilities...[/bold cyan]"
        )
        result = subprocess.run(
            ["safety", "check", "--json"],
            capture_output=True,
            text=True,
        )

        # Safety returns non-zero on findings
        if result.returncode in (0, 1):
            import json

            try:
                data = json.loads(result.stdout)
                vulnerabilities = data if isinstance(data, list) else []

                if vulnerabilities:
                    console.print(
                        f"\n[yellow]⚠ Found {len(vulnerabilities)} vulnerability(ies):[/yellow]\n"
                    )
                    for vuln in vulnerabilities:
                        package = vuln.get("package", "Unknown")
                        installed = vuln.get("installed_version", "Unknown")
                        vulnerability_id = vuln.get("vulnerability", "Unknown")
                        severity = vuln.get("severity", "UNKNOWN")

                        severity_color = {
                            "critical": "red",
                            "high": "red",
                            "medium": "yellow",
                            "low": "blue",
                        }.get(severity.lower(), "white")

                        console.print(
                            f"[{severity_color}]{severity.upper()}[/{severity_color}] "
                            f"{package}=={installed} - {vulnerability_id}"
                        )
                else:
                    console.print("[green]✓ No known vulnerabilities found[/green]")
            except (json.JSONDecodeError, TypeError):
                # Fallback to stdout if JSON parsing fails
                if result.stdout:
                    console.print(result.stdout)
                if result.stderr:
                    console.print(result.stderr)
        else:
            console.print(f"[red]✗ Error: {result.stderr}[/red]")
            raise typer.Exit(1)

    except FileNotFoundError:
        console.print("[red]✗ Safety is not installed[/red]")
        console.print("[yellow]Install it with: uv add --dev safety[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        raise typer.Exit(1)
