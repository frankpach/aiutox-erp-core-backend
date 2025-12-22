"""Main CLI entry point for AiutoX ERP."""

# #region agent log
import json
import time
from pathlib import Path
try:
    debug_log_path = Path(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log")
    debug_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(debug_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"aiutox.py:1","message":"aiutox.py MODULE LOAD START","data":{},"timestamp":int(time.time()*1000)})+"\n")
except: pass
# #endregion

import typer
from rich.console import Console

# #region agent log
try:
    with open(debug_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"aiutox.py:10","message":"aiutox.py BEFORE import commands","data":{},"timestamp":int(time.time()*1000)})+"\n")
except: pass
# #endregion

from scripts.cli.commands import analyze, db, make, migrate, repl, route, run, test

# #region agent log
try:
    with open(debug_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"aiutox.py:13","message":"aiutox.py AFTER import commands","data":{},"timestamp":int(time.time()*1000)})+"\n")
except: pass
# #endregion

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
app.add_typer(run.app, name="run")

# Register serv command directly (alias for run dev --all)
@app.command()
def serv(
    skip_docker: bool = typer.Option(False, "--skip-docker", help="Skip Docker services"),
    skip_backend: bool = typer.Option(False, "--skip-backend", help="Skip backend server"),
    skip_frontend: bool = typer.Option(False, "--skip-frontend", help="Skip frontend server"),
    run_tests: bool = typer.Option(False, "--tests", help="Run E2E tests after starting services"),
):
    """Start all development services (Docker, Backend, Frontend)."""
    # Import here to avoid circular imports
    from scripts.cli.commands.run import _start_all_services
    _start_all_services(skip_docker, skip_backend, skip_frontend, run_tests)


def main() -> None:
    """Main entry point."""
    # #region agent log
    try:
        with open(debug_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"aiutox.py:39","message":"main() ENTRY","data":{},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    # #region agent log
    try:
        with open(debug_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"aiutox.py:42","message":"main() BEFORE app()","data":{},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    app()
    # #region agent log
    try:
        with open(debug_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"aiutox.py:44","message":"main() AFTER app()","data":{},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion


if __name__ == "__main__":
    main()

