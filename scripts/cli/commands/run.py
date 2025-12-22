"""Run development commands for AiutoX ERP."""

# #region agent log
import json
import time
from pathlib import Path
try:
    debug_log_path = Path(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log")
    debug_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(debug_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:1","message":"run.py MODULE LOAD START","data":{},"timestamp":int(time.time()*1000)})+"\n")
except: pass
# #endregion

import os
import sys
import subprocess
import time
import socket
import signal
import platform
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from datetime import datetime
from dataclasses import dataclass, field
import threading
from threading import Thread
from queue import Queue, Empty

import typer
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.live import Live
from rich.text import Text
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich import box
import re

# Optional dependencies for enhanced features
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Try keyboard library for shortcuts (Windows/Linux/Mac)
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    # Fallback to pynput if keyboard not available
    try:
        from pynput import keyboard as pynput_keyboard
        PYNPUT_AVAILABLE = True
    except ImportError:
        PYNPUT_AVAILABLE = False

console = Console()
app = typer.Typer(name="run", help="Run development services")

# Global state for error tracking and process management
_errors: List[str] = []
_process_info: Dict[str, Dict] = {}
_log_files: Dict[str, Path] = {}
_stop_log_streaming = threading.Event()
_current_menu_state: str = "main"  # Track current menu state
_selected_service: Optional[str] = None  # Currently selected service for actions
_test_results_history: List[Dict] = []  # History of test executions
_health_cache: Dict[str, Tuple[Dict, float]] = {}  # Cache for health checks: {service_name: (health_data, timestamp)}
_health_cache_ttl: float = 2.0  # Cache TTL in seconds (update every 2 seconds)


@dataclass
class ProcessInfo:
    """Information about a running process."""
    name: str
    process: subprocess.Popen
    pid: int
    log_file: Optional[Path] = None
    status: str = "running"

    def is_running(self) -> bool:
        """Check if process is still running."""
        return self.process.poll() is None

# Default configuration
DEFAULT_CONFIG = {
    "backend": {
        "host": "0.0.0.0",
        "port": 8000,
        "health_url": "http://localhost:8000/healthz",
        "docs_url": "http://localhost:8000/docs",
    },
    "frontend": {
        "host": "127.0.0.1",
        "port": 3000,
        "url": "http://127.0.0.1:3000",
    },
    "docker": {
        "postgres": {
            "container": "aiutox_db_dev",
            "port": 15432,
            "user": "devuser",
        },
        "redis": {
            "container": "aiutox_redis_dev",
            "port": 6379,
        },
    },
}


def load_env_config(project_root: Path) -> Dict[str, Dict[str, str]]:
    """Load environment configuration from .env files with priority.

    Priority: backend/.env > frontend/.env > .env (root)

    Args:
        project_root: Root directory of the project

    Returns:
        Dictionary with backend and frontend configurations
    """
    config = {
        "backend": {},
        "frontend": {},
    }

    # Load .env files in priority order
    env_files = [
        (project_root / "backend" / ".env", "backend"),
        (project_root / "frontend" / ".env", "frontend"),
        (project_root / ".env", "default"),
    ]

    for env_file, source in env_files:
        if env_file.exists():
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")

                            # Map backend variables
                            if source in ("backend", "default"):
                                if key.startswith("BACKEND_") or key in ("HOST", "PORT"):
                                    config["backend"][key] = value
                                elif key in ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER",
                                           "POSTGRES_PASSWORD", "POSTGRES_DB", "DATABASE_URL",
                                           "REDIS_URL", "REDIS_PASSWORD"):
                                    config["backend"][key] = value

                            # Map frontend variables
                            if source in ("frontend", "default"):
                                if key.startswith("VITE_") or key.startswith("FRONTEND_"):
                                    config["frontend"][key] = value
                                elif key in ("HOST", "PORT"):
                                    config["frontend"][key] = value
            except Exception as e:
                console.print(f"[yellow][WARN] Error loading {env_file}: {e}[/yellow]")

    # Apply defaults
    backend_config = DEFAULT_CONFIG["backend"].copy()
    backend_config.update(config["backend"])

    frontend_config = DEFAULT_CONFIG["frontend"].copy()
    frontend_config.update(config["frontend"])

    return {
        "backend": backend_config,
        "frontend": frontend_config,
    }


def test_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """Test if a port is open."""
    # #region agent log
    import json
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"run.py:144","message":"test_port ENTRY","data":{"host":host,"port":port,"timeout":timeout},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"run.py:149","message":"test_port BEFORE connect_ex","data":{"host":host,"port":port},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        result = sock.connect_ex((host, port))
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"run.py:153","message":"test_port AFTER connect_ex","data":{"host":host,"port":port,"result":result},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        sock.close()
        return result == 0
    except Exception as e:
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"run.py:159","message":"test_port EXCEPTION","data":{"host":host,"port":port,"error":str(e)},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        return False


def wait_for_service(
    url: str,
    service_name: str,
    max_attempts: int = 30,
    delay_seconds: int = 2,
) -> bool:
    """Wait for a service to be available."""
    console.print(f"[cyan]Esperando a que {service_name} esté disponible en {url}...[/cyan]")

    for i in range(1, max_attempts + 1):
        try:
            with urlopen(url, timeout=2) as response:
                if response.getcode() == 200:
                    console.print(f"[green][OK] {service_name} está disponible[/green]")
                    return True
        except (URLError, HTTPError, OSError):
            if i < max_attempts:
                console.print(f"  [dim]Intento {i}/{max_attempts}...[/dim]")
                time.sleep(delay_seconds)

    console.print(
        f"[red][FAIL] {service_name} no está disponible después de "
        f"{max_attempts * delay_seconds} segundos[/red]"
    )
    return False


def check_docker_running() -> bool:
    """Check if Docker is running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def check_container_running(container_name: str) -> bool:
    """Check if a Docker container is running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return container_name in result.stdout
    except Exception:
        return False


def verify_docker_service(
    container_name: str,
    service_name: str,
    port: int,
    check_command: Optional[Tuple[str, ...]] = None,
    check_success: Optional[str] = None,
) -> bool:
    """Generic function to verify a Docker service.

    Args:
        container_name: Name of the Docker container
        service_name: Display name of the service
        port: Port to check
        check_command: Optional command to run in container (tuple of strings)
        check_success: Optional string to look for in command output

    Returns:
        True if service is working, False otherwise
    """
    console.print(f"[cyan]Probando conexión con {service_name}...[/cyan]")

    # Check if container is running
    if not check_container_running(container_name):
        console.print(f"[red][FAIL] Contenedor {service_name} ({container_name}) no está corriendo[/red]")
        return False

    # Check if port is accessible
    if not test_port("localhost", port):
        console.print(f"[yellow][WARN] {service_name} está corriendo pero el puerto {port} no está accesible[/yellow]")
        return False

    # Run optional check command
    if check_command:
        try:
            result = subprocess.run(
                ["docker", "exec", container_name] + list(check_command),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if check_success:
                if check_success in result.stdout:
                    console.print(f"[green][OK] {service_name} está corriendo y respondiendo[/green]")
                    return True
                else:
                    console.print(f"[yellow][WARN] {service_name} está corriendo pero no responde correctamente[/yellow]")
                    return False
            else:
                if result.returncode == 0:
                    console.print(f"[green][OK] {service_name} está corriendo y respondiendo[/green]")
                    return True
                else:
                    console.print(f"[yellow][WARN] {service_name} está corriendo pero no responde correctamente[/yellow]")
                    return False
        except Exception as e:
            console.print(f"[yellow][WARN] No se pudo verificar {service_name}: {e}[/yellow]")
            return False

    console.print(f"[green][OK] {service_name} está corriendo y respondiendo[/green]")
    return True


def wait_for_port(
    host: str,
    port: int,
    service_name: str,
    max_attempts: int = 15,
    delay_seconds: int = 2,
) -> bool:
    """Wait for a port to become available."""
    console.print(f"[cyan]Verificando {service_name}...[/cyan]")

    for i in range(1, max_attempts + 1):
        if test_port(host, port):
            console.print(f"[green][OK] {service_name} está escuchando en puerto {port}[/green]")
            return True
        if i < max_attempts:
            console.print(f"  [dim]Esperando {service_name}... (intento {i}/{max_attempts - 1})[/dim]")
            time.sleep(delay_seconds)

    console.print(
        f"[yellow][WARN] {service_name} no está respondiendo en puerto {port} después de "
        f"{max_attempts * delay_seconds} segundos[/yellow]"
    )
    return False


def find_executable(executable: str) -> Optional[str]:
    """Find executable in PATH."""
    return shutil.which(executable)


def start_process_in_background(
    cmd: list[str],
    cwd: Path,
    process_name: str,
    log_file: Optional[Path] = None,
) -> subprocess.Popen:
    """Start a process in background (platform-specific).

    Args:
        cmd: Command to run
        cwd: Working directory
        process_name: Name of the process for error messages
        log_file: Optional log file to redirect stdout/stderr

    Raises:
        FileNotFoundError: If the executable is not found
        Exception: For other errors with clear error messages
    """
    # Check if first command exists
    executable = cmd[0] if cmd else None
    if not executable:
        raise ValueError(f"[ERROR] Comando vacío para {process_name}")

    # Find executable in PATH
    executable_path = find_executable(executable)
    if not executable_path:
        raise FileNotFoundError(
            f"[ERROR] No se encontró '{executable}' en el PATH.\n"
            f"       Por favor asegúrate de que {executable} está instalado y disponible en PATH.\n"
            f"       Proceso: {process_name}\n"
            f"       Comando: {' '.join(cmd)}"
        )

    try:
        if sys.platform == "win32":
            import subprocess as sp
            # On Windows, use shell=True with CREATE_NEW_CONSOLE for better compatibility
            # Convert Path to string for cwd
            if log_file:
                # Open log file in append mode
                log_f = open(log_file, "a", encoding="utf-8")
                return sp.Popen(
                    cmd,
                    cwd=str(cwd),
                    shell=True,  # Required for npm and other commands in Windows
                    stdout=log_f,
                    stderr=sp.STDOUT,
                    creationflags=sp.CREATE_NEW_CONSOLE,
                )
            else:
                return sp.Popen(
                    cmd,
                    cwd=str(cwd),
                    shell=True,  # Required for npm and other commands in Windows
                    creationflags=sp.CREATE_NEW_CONSOLE,
                )
        else:
            if log_file:
                # Open log file in append mode
                log_f = open(log_file, "a", encoding="utf-8")
                return subprocess.Popen(
                    cmd,
                    cwd=str(cwd),
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                )
            else:
                return subprocess.Popen(
                    cmd,
                    cwd=str(cwd),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"[ERROR] No se pudo iniciar {process_name}.\n"
            f"       Ejecutable no encontrado: {executable}\n"
            f"       Comando: {' '.join(cmd)}\n"
            f"       Directorio: {cwd}\n"
            f"       Error original: {e}"
        )
    except Exception as e:
        raise Exception(
            f"[ERROR] Error al iniciar {process_name}.\n"
            f"       Comando: {' '.join(cmd)}\n"
            f"       Directorio: {cwd}\n"
            f"       Error: {e}"
        )


def test_docker_connections() -> bool:
    """Test connections to Docker containers (PostgreSQL and Redis)."""
    console.print()
    console.print(Panel.fit("[cyan]Prueba de Conexiones Docker[/cyan]", border_style="cyan"))
    console.print()

    if not check_docker_running():
        console.print("[red][ERROR] Docker no está corriendo. Por favor inicia Docker Desktop.[/red]")
        return False

    all_ok = True

    # Test PostgreSQL
    pg_config = DEFAULT_CONFIG["docker"]["postgres"]
    pg_ok = verify_docker_service(
        container_name=pg_config["container"],
        service_name="PostgreSQL",
        port=pg_config["port"],
        check_command=("pg_isready", "-U", pg_config["user"]),
    )
    if not pg_ok:
        all_ok = False

    console.print()

    # Test Redis
    redis_config = DEFAULT_CONFIG["docker"]["redis"]
    redis_ok = verify_docker_service(
        container_name=redis_config["container"],
        service_name="Redis",
        port=redis_config["port"],
        check_command=("redis-cli", "ping"),
        check_success="PONG",
    )
    if not redis_ok:
        all_ok = False

    console.print()

    # Summary
    if all_ok:
        console.print("[green][OK] Todas las conexiones Docker están funcionando correctamente[/green]")
    else:
        console.print("[yellow][WARN] Algunas conexiones Docker tienen problemas[/yellow]")
        console.print("[yellow]       Ejecuta: cd backend && docker-compose -f docker-compose.dev.yml up -d[/yellow]")

    return all_ok


def start_docker_services(backend_dir: Path) -> bool:
    """Start Docker services."""
    console.print()
    console.print(Panel.fit("[cyan]PASO 1: Servicios Docker[/cyan]", border_style="cyan"))
    console.print()

    if not check_docker_running():
        console.print("[red][ERROR] Docker no está corriendo. Por favor inicia Docker Desktop.[/red]")
        return False

    docker_compose_file = backend_dir / "docker-compose.dev.yml"
    if not docker_compose_file.exists():
        console.print(f"[red][ERROR] docker-compose.dev.yml no encontrado en: {docker_compose_file}[/red]")
        return False

    # Check if containers are already running
    pg_config = DEFAULT_CONFIG["docker"]["postgres"]
    redis_config = DEFAULT_CONFIG["docker"]["redis"]

    pg_running = check_container_running(pg_config["container"])
    redis_running = check_container_running(redis_config["container"])

    if pg_running and redis_running:
        console.print("[green][OK] Servicios Docker ya están corriendo[/green]")
        console.print(f"  - PostgreSQL: {pg_config['container']}")
        console.print(f"  - Redis: {redis_config['container']}")
        console.print()

        # Verify services are accessible
        pg_ready = wait_for_port("localhost", pg_config["port"], "PostgreSQL", max_attempts=5, delay_seconds=1)
        redis_ready = wait_for_port("localhost", redis_config["port"], "Redis", max_attempts=5, delay_seconds=1)

        if pg_ready and redis_ready:
            return True
        else:
            console.print("[yellow][WARN] Contenedores están corriendo pero algunos servicios no responden[/yellow]")
            console.print("[yellow]       Intentando reiniciar servicios...[/yellow]")
            console.print()

    # Start or restart Docker services
    console.print("[cyan]Iniciando servicios Docker...[/cyan]")
    console.print()

    # Start Docker services (docker-compose up is idempotent, but we use --build to ensure latest)
    result = subprocess.run(
        ["docker-compose", "-f", str(docker_compose_file), "up", "-d", "--build"],
        cwd=backend_dir,
    )

    if result.returncode != 0:
        console.print("[red][ERROR] Error al iniciar servicios Docker[/red]")
        return False

    console.print("[green][OK] Servicios Docker iniciados[/green]")
    console.print()

    # Wait for services to stabilize
    console.print("[cyan]Esperando a que los servicios Docker se estabilicen...[/cyan]")
    time.sleep(5)

    # Verify PostgreSQL
    pg_config = DEFAULT_CONFIG["docker"]["postgres"]
    pg_ready = wait_for_port("localhost", pg_config["port"], "PostgreSQL")
    if not pg_ready:
        console.print(
            "[yellow]       Verifica los logs: docker-compose -f backend/docker-compose.dev.yml logs db[/yellow]"
        )

    # Verify Redis
    redis_config = DEFAULT_CONFIG["docker"]["redis"]
    redis_ready = wait_for_port("localhost", redis_config["port"], "Redis")
    if not redis_ready:
        console.print(
            "[yellow]       Verifica los logs: docker-compose -f backend/docker-compose.dev.yml logs redis[/yellow]"
        )
        console.print("[yellow]       NOTA: Redis es opcional para desarrollo básico[/yellow]")
    else:
        # Try to verify Redis connection
        console.print("[cyan]Verificando conexión a Redis...[/cyan]")
        try:
            result = subprocess.run(
                ["docker", "exec", redis_config["container"], "redis-cli", "ping"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "PONG" in result.stdout:
                console.print("[green][OK] Conexión a Redis verificada correctamente[/green]")
            else:
                console.print(
                    "[yellow][WARN] Redis responde pero la conexión puede tener problemas[/yellow]"
                )
        except Exception:
            console.print("[yellow][WARN] No se pudo verificar la conexión a Redis (puede ser normal)[/yellow]")

    return True


def check_service_running(url: str, service_name: str) -> bool:
    """Check if a service is already running."""
    try:
        with urlopen(url, timeout=2) as response:
            return response.getcode() == 200
    except (URLError, HTTPError, OSError):
        return False


def stop_process_by_port(port: int, process_name: str) -> bool:
    """Stop a process running on a specific port.

    Returns:
        True if process was stopped, False otherwise
    """
    try:
        if platform.system() == "Windows":
            # Windows: use netstat to find PID, then taskkill
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        try:
                            # Kill the process
                            subprocess.run(
                                ["taskkill", "/F", "/PID", pid],
                                capture_output=True,
                                timeout=5
                            )
                            console.print(f"[yellow]Proceso {process_name} (PID: {pid}) detenido en puerto {port}[/yellow]")
                            time.sleep(1)  # Wait a bit for port to be released
                            return True
                        except Exception:
                            pass
        else:
            # Linux/Mac: use lsof to find PID, then kill
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout.strip():
                pid = result.stdout.strip()
                try:
                    subprocess.run(
                        ["kill", "-9", pid],
                        capture_output=True,
                        timeout=5
                    )
                    console.print(f"[yellow]Proceso {process_name} (PID: {pid}) detenido en puerto {port}[/yellow]")
                    time.sleep(1)  # Wait a bit for port to be released
                    return True
                except Exception:
                    pass
    except Exception as e:
        console.print(f"[yellow][WARN] No se pudo detener proceso en puerto {port}: {e}[/yellow]")

    return False


def stop_service(service_name: str, graceful: bool = True) -> bool:
    """Stop a service by name.

    Args:
        service_name: Name of the service ("Backend", "Frontend")
        graceful: If True, try graceful termination first

    Returns:
        True if service was stopped or wasn't running, False on error
    """
    if service_name not in _process_info:
        # Try to stop by port
        if service_name == "Backend":
            config = DEFAULT_CONFIG["backend"]
            if test_port("localhost", config["port"]):
                result = stop_process_by_port(config["port"], "Backend")
                # Clear cache
                if service_name in _health_cache:
                    del _health_cache[service_name]
                return result
        elif service_name == "Frontend":
            config = DEFAULT_CONFIG["frontend"]
            if test_port("127.0.0.1", config["port"]):
                result = stop_process_by_port(config["port"], "Frontend")
                # Clear cache
                if service_name in _health_cache:
                    del _health_cache[service_name]
                return result
        return True

    process = _process_info[service_name].get("process")
    if not process:
        return True

    try:
        if process.poll() is None:  # Still running
            if graceful:
                console.print(f"[cyan]Deteniendo {service_name} (graceful)...[/cyan]")
                process.terminate()
                time.sleep(2)
                if process.poll() is None:
                    console.print(f"[yellow]Proceso no respondió, forzando cierre...[/yellow]")
                    process.kill()
            else:
                console.print(f"[cyan]Forzando cierre de {service_name}...[/cyan]")
                process.kill()

            time.sleep(1)
            console.print(f"[green][OK] {service_name} detenido[/green]")

            # Clear cache and process info
            if service_name in _health_cache:
                del _health_cache[service_name]
            if service_name in _process_info:
                del _process_info[service_name]

            return True
        else:
            console.print(f"[yellow][WARN] {service_name} ya estaba detenido[/yellow]")
            # Clear cache and process info even if already stopped
            if service_name in _health_cache:
                del _health_cache[service_name]
            if service_name in _process_info:
                del _process_info[service_name]
            return True
    except Exception as e:
        console.print(f"[red][ERROR] Error al detener {service_name}: {e}[/red]")
        return False


def kill_service(service_name: str) -> bool:
    """Kill a service forcefully.

    Returns:
        True if service was killed or wasn't running, False on error
    """
    return stop_service(service_name, graceful=False)


def restart_service(service_name: str, project_root: Path, config: Dict) -> bool:
    """Restart a service.

    Returns:
        True if service was restarted successfully, False otherwise
    """
    console.print(f"[cyan]Reiniciando {service_name}...[/cyan]")

    # Stop the service
    if not stop_service(service_name, graceful=True):
        console.print(f"[yellow][WARN] No se pudo detener {service_name} correctamente[/yellow]")

    time.sleep(2)  # Wait for port to be released

    # Clear process info and health cache
    if service_name in _process_info:
        del _process_info[service_name]
    if service_name in _health_cache:
        del _health_cache[service_name]

    # Restart based on service type
    if service_name == "Backend":
        backend_dir = project_root / "backend"
        return start_backend(backend_dir, config.get("backend"), project_root=project_root, force=True)
    elif service_name == "Frontend":
        frontend_dir = project_root / "frontend"
        return start_frontend(frontend_dir, config.get("frontend"), project_root=project_root, force=True)

    return False


def stop_all_services() -> None:
    """Stop all running services."""
    console.print("[cyan]Deteniendo todos los servicios...[/cyan]")
    for service_name in list(_process_info.keys()):
        stop_service(service_name, graceful=True)
    console.print("[green][OK] Todos los servicios detenidos[/green]")


def restart_all_services(project_root: Path, config: Dict) -> None:
    """Restart all services."""
    console.print("[cyan]Reiniciando todos los servicios...[/cyan]")
    stop_all_services()
    time.sleep(3)

    backend_dir = project_root / "backend"
    frontend_dir = project_root / "frontend"

    start_backend(backend_dir, config.get("backend"), project_root=project_root, force=True)
    start_frontend(frontend_dir, config.get("frontend"), project_root=project_root, force=True)


def stop_backend_process(backend_dir: Path, config: Optional[Dict[str, str]] = None) -> bool:
    """Stop the backend process if it's running.

    Returns:
        True if backend was stopped or wasn't running, False on error
    """
    if config is None:
        config = DEFAULT_CONFIG["backend"]

    # Check if we have a registered process
    if "Backend" in _process_info:
        process = _process_info["Backend"].get("process")
        if process and process.poll() is None:
            try:
                console.print("[cyan]Deteniendo proceso backend registrado...[/cyan]")
                process.terminate()
                time.sleep(2)
                if process.poll() is None:
                    process.kill()
                console.print("[green][OK] Proceso backend detenido[/green]")
                return True
            except Exception as e:
                console.print(f"[yellow][WARN] Error al detener proceso registrado: {e}[/yellow]")

    # Try to stop by port
    if test_port("localhost", config["port"]):
        console.print(f"[cyan]Deteniendo proceso en puerto {config['port']}...[/cyan]")
        return stop_process_by_port(config["port"], "Backend")

    return True


def start_backend(backend_dir: Path, config: Optional[Dict[str, str]] = None, skip_if_running: bool = True, project_root: Optional[Path] = None, force: bool = False) -> bool:
    """Start backend server."""
    if config is None:
        config = DEFAULT_CONFIG["backend"]

    console.print()
    console.print(Panel.fit("[cyan]PASO 2: Backend FastAPI[/cyan]", border_style="cyan"))
    console.print()

    # Check if backend is already running
    backend_running = check_service_running(config["health_url"], "Backend") or test_port("localhost", config["port"])

    if backend_running:
        if force:
            # Force restart: stop and restart
            console.print("[cyan]Backend detectado corriendo. Reiniciando (--force)...[/cyan]")
            stop_backend_process(backend_dir, config)
            # Clear old process info
            if "Backend" in _process_info:
                del _process_info["Backend"]
            time.sleep(2)  # Wait for port to be released
        elif skip_if_running:
            # Skip if running: just inform and continue
            if check_service_running(config["health_url"], "Backend"):
                console.print(f"[green][OK] Backend ya está corriendo en {config['docs_url'].replace('/docs', '')}[/green]")
                console.print(f"  - API: {config['docs_url'].replace('/docs', '')}")
                console.print(f"  - Docs: {config['docs_url']}")
                console.print("[dim]  (Usa --force para reiniciar)[/dim]")
                return True
        else:
            # Not skipping and not forcing: try to start anyway (might fail if port in use)
            console.print("[yellow][WARN] Backend parece estar corriendo pero se intentará iniciar de nuevo[/yellow]")
            console.print("[yellow]       Si falla, usa --force para reiniciarlo[/yellow]")

    # Check if uv is available
    uv_available = False
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True, timeout=5)
        uv_available = True
    except Exception:
        console.print("[yellow][WARN] 'uv' no está disponible. Intentando con Python directamente...[/yellow]")

    console.print("[cyan]Iniciando servidor backend...[/cyan]")

    # Determine command to run
    if uv_available:
        cmd = [
            "uv", "run", "uvicorn", "app.main:app",
            "--reload", "--host", config["host"], "--port", str(config["port"])
        ]
    else:
        # Check Python
        try:
            subprocess.run(["python", "--version"], capture_output=True, check=True, timeout=5)
        except Exception:
            console.print("[red][ERROR] Python no está disponible. Por favor instala Python 3.12+[/red]")
            return False

        cmd = [
            "python", "-m", "uvicorn", "app.main:app",
            "--reload", "--host", config["host"], "--port", str(config["port"])
        ]

    # Prepare log file
    log_file = None
    if project_root:
        logs_dir = get_logs_dir(project_root)
        log_file = logs_dir / "backend.log"
        _log_files["backend"] = log_file

    # Start backend in background
    try:
        process = start_process_in_background(cmd, backend_dir, "Backend", log_file=log_file)
        # Register process info
        _process_info["Backend"] = {
            "process": process,
            "pid": process.pid,
            "log_file": log_file,
        }
        # Clear health cache to force refresh
        if "Backend" in _health_cache:
            del _health_cache["Backend"]
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        console.print()
        console.print("[yellow]Solución:[/yellow]")
        if not uv_available:
            console.print("  1. Verifica que Python esté instalado: python --version")
            console.print("  2. Verifica que uvicorn esté instalado: pip install uvicorn")
        else:
            console.print("  1. Verifica que uv esté instalado: uv --version")
            console.print("  2. Verifica que las dependencias estén instaladas: cd backend && uv sync")
        add_error(f"Backend: {str(e)}")
        return False
    except Exception as e:
        console.print(f"[red][ERROR] Error al iniciar backend: {e}[/red]")
        add_error(f"Backend: {str(e)}")
        return False

    console.print("[cyan]Esperando a que el backend esté disponible...[/cyan]")
    time.sleep(3)

    # Verify backend is available
    backend_ready = wait_for_service(
        config["docs_url"],
        "Backend API",
        max_attempts=20,
    )

    if backend_ready:
        console.print(f"[green][OK] Backend está corriendo en {config['docs_url'].replace('/docs', '')}[/green]")
        console.print(f"  - API: {config['docs_url'].replace('/docs', '')}")
        console.print(f"  - Docs: {config['docs_url']}")
    else:
        console.print(
            "[yellow][WARN] Backend no está respondiendo. Verifica los logs en la ventana del backend.[/yellow]"
        )

    return backend_ready


def start_frontend(frontend_dir: Path, config: Optional[Dict[str, str]] = None, skip_if_running: bool = True, project_root: Optional[Path] = None, force: bool = False) -> bool:
    """Start frontend server."""
    if config is None:
        config = DEFAULT_CONFIG["frontend"]

    console.print()
    console.print(Panel.fit("[cyan]PASO 3: Frontend React[/cyan]", border_style="cyan"))
    console.print()

    frontend_port = config["port"]
    frontend_url = config["url"]

    # Check if frontend is already running
    frontend_running = check_service_running(frontend_url, "Frontend") or test_port(config["host"], frontend_port)

    if frontend_running:
        if force:
            # Force restart: stop and restart
            console.print("[cyan]Frontend detectado corriendo. Reiniciando (--force)...[/cyan]")
            # Try to stop by port
            stop_process_by_port(frontend_port, "Frontend")
            # Clear old process info
            if "Frontend" in _process_info:
                del _process_info["Frontend"]
            time.sleep(2)  # Wait for port to be released
        elif skip_if_running:
            # Skip if running: just inform and continue
            if check_service_running(frontend_url, "Frontend"):
                console.print(f"[green][OK] Frontend ya está corriendo en {frontend_url}[/green]")
                console.print("[dim]  (Usa --force para reiniciar)[/dim]")
                return True
        else:
            # Not skipping and not forcing: try to start anyway (might fail if port in use)
            console.print("[yellow][WARN] Frontend parece estar corriendo pero se intentará iniciar de nuevo[/yellow]")
            console.print("[yellow]       Si falla, usa --force para reiniciarlo[/yellow]")

    # Check if npm is available
    npm_path = find_executable("npm")
    if not npm_path:
        console.print("[red][ERROR] 'npm' no está disponible en el PATH[/red]")
        console.print("[yellow]       Por favor instala Node.js desde: https://nodejs.org/[/yellow]")
        console.print("[yellow]       O verifica que Node.js esté instalado y en tu PATH[/yellow]")
        return False

    console.print(f"[cyan]Usando npm desde: {npm_path}[/cyan]")

    # Check if node_modules exists
    if not (frontend_dir / "node_modules").exists():
        console.print("[yellow][WARN] node_modules no encontrado. Instalando dependencias...[/yellow]")
        try:
            result = subprocess.run(
                ["npm", "install"],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
            )
            if result.returncode != 0:
                console.print("[red][ERROR] Error al instalar dependencias del frontend[/red]")
                console.print(f"[red]       Salida: {result.stdout}[/red]")
                console.print(f"[red]       Errores: {result.stderr}[/red]")
                return False
        except subprocess.TimeoutExpired:
            console.print("[red][ERROR] Timeout al instalar dependencias (más de 5 minutos)[/red]")
            return False
        except Exception as e:
            console.print(f"[red][ERROR] Excepción al instalar dependencias: {e}[/red]")
            return False

    console.print("[cyan]Iniciando servidor frontend...[/cyan]")

    # Prepare log file
    log_file = None
    if project_root:
        logs_dir = get_logs_dir(project_root)
        log_file = logs_dir / "frontend.log"
        _log_files["frontend"] = log_file

    # Start frontend in background
    try:
        process = start_process_in_background(["npm", "run", "dev"], frontend_dir, "Frontend", log_file=log_file)
        # Register process info
        _process_info["Frontend"] = {
            "process": process,
            "pid": process.pid,
            "log_file": log_file,
        }
        # Clear health cache to force refresh
        if "Frontend" in _health_cache:
            del _health_cache["Frontend"]
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        console.print()
        console.print("[yellow]Solución:[/yellow]")
        console.print("  1. Verifica que Node.js esté instalado: node --version")
        console.print("  2. Verifica que npm esté disponible: npm --version")
        console.print("  3. Reinicia la terminal después de instalar Node.js")
        add_error(f"Frontend: {str(e)}")
        return False
    except Exception as e:
        console.print(f"[red][ERROR] Error al iniciar frontend: {e}[/red]")
        add_error(f"Frontend: {str(e)}")
        return False

    console.print("[cyan]Esperando a que el frontend esté disponible...[/cyan]")
    time.sleep(5)

    # Verify frontend is available
    frontend_ready = wait_for_service(
        frontend_url,
        "Frontend",
        max_attempts=15,
    )

    if frontend_ready:
        console.print(f"[green][OK] Frontend está corriendo en {frontend_url}[/green]")
    else:
        console.print(
            "[yellow][WARN] Frontend no está respondiendo. Verifica los logs en la ventana del frontend.[/yellow]"
        )

    return frontend_ready


def show_summary(skip_docker: bool, skip_backend: bool, skip_frontend: bool, config: Dict):
    """Show summary of all services."""
    console.print()
    console.print(Panel.fit("[cyan]RESUMEN[/cyan]", border_style="cyan"))
    console.print()

    services = []

    # Check Docker
    if not skip_docker:
        pg_config = DEFAULT_CONFIG["docker"]["postgres"]
        if test_port("localhost", pg_config["port"]):
            services.append({"name": "PostgreSQL (Docker)", "status": "OK", "port": str(pg_config["port"])})
        else:
            services.append({"name": "PostgreSQL (Docker)", "status": "FAIL", "port": str(pg_config["port"])})

        redis_config = DEFAULT_CONFIG["docker"]["redis"]
        if test_port("localhost", redis_config["port"]):
            services.append({"name": "Redis (Docker)", "status": "OK", "port": str(redis_config["port"])})
        else:
            services.append({"name": "Redis (Docker)", "status": "FAIL", "port": str(redis_config["port"])})

    # Check Backend
    if not skip_backend:
        backend_config = config.get("backend", DEFAULT_CONFIG["backend"])
        backend_health = check_service_running(backend_config["docs_url"], "Backend")

        if backend_health:
            services.append(
                {
                    "name": "Backend API",
                    "status": "OK",
                    "port": str(backend_config["port"]),
                    "url": backend_config["docs_url"].replace("/docs", ""),
                }
            )
        else:
            services.append(
                {
                    "name": "Backend API",
                    "status": "FAIL",
                    "port": str(backend_config["port"]),
                    "url": backend_config["docs_url"].replace("/docs", ""),
                }
            )

    # Check Frontend
    if not skip_frontend:
        frontend_config = config.get("frontend", DEFAULT_CONFIG["frontend"])
        frontend_health = check_service_running(frontend_config["url"], "Frontend")

        if frontend_health:
            services.append(
                {
                    "name": "Frontend",
                    "status": "OK",
                    "port": str(frontend_config["port"]),
                    "url": frontend_config["url"],
                }
            )
        else:
            services.append(
                {
                    "name": "Frontend",
                    "status": "FAIL",
                    "port": str(frontend_config["port"]),
                    "url": frontend_config["url"],
                }
            )

    # Show table
    table = Table(show_header=True, header_style="cyan")
    table.add_column("Estado", style="bold")
    table.add_column("Servicio")
    table.add_column("Puerto")
    table.add_column("URL", style="dim")

    for service in services:
        status_color = "green" if service["status"] == "OK" else "red"
        status_text = f"[{status_color}]{service['status']}[/{status_color}]"
        url = service.get("url", "")
        table.add_row(status_text, service["name"], service["port"], url)

    console.print(table)

    console.print()
    console.print(Panel.fit("[cyan]URLs Importantes[/cyan]", border_style="cyan"))
    console.print()
    frontend_config = config.get("frontend", DEFAULT_CONFIG["frontend"])
    backend_config = config.get("backend", DEFAULT_CONFIG["backend"])
    console.print(f"  [cyan]Frontend:     [/cyan]{frontend_config['url']}")
    console.print(f"  [cyan]Backend API:  [/cyan]{backend_config['docs_url'].replace('/docs', '')}")
    console.print(f"  [cyan]API Docs:     [/cyan]{backend_config['docs_url']}")
    console.print("  [cyan]pgAdmin:      [/cyan]http://localhost:8888")
    console.print()


def get_logs_dir(project_root: Path) -> Path:
    """Get or create logs directory."""
    logs_dir = project_root / ".logs"
    logs_dir.mkdir(exist_ok=True)
    return logs_dir


def get_process_metrics(pid: int, use_cache: bool = True) -> Dict[str, Optional[float]]:
    """Get CPU and memory usage for a process.

    Args:
        pid: Process ID
        use_cache: If True, use cached CPU value (non-blocking), otherwise wait for interval

    Returns:
        Dict with 'cpu_percent' and 'memory_mb' keys, or None values if unavailable
    """
    # #region agent log
    import json
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"run.py:1148","message":"get_process_metrics ENTRY","data":{"pid":pid,"use_cache":use_cache,"psutil_available":PSUTIL_AVAILABLE},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    if not PSUTIL_AVAILABLE:
        return {"cpu_percent": None, "memory_mb": None}

    try:
        proc = psutil.Process(pid)
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"run.py:1156","message":"get_process_metrics BEFORE cpu_percent","data":{"pid":pid,"use_cache":use_cache},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        # Use non-blocking cpu_percent (returns immediately with cached value)
        # First call with interval=None may return 0.0, but that's acceptable for non-blocking
        cpu_percent = proc.cpu_percent(interval=None if use_cache else 0.1)
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"run.py:1160","message":"get_process_metrics AFTER cpu_percent","data":{"pid":pid,"cpu_percent":cpu_percent},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        # If we got 0.0 and it's the first time, it might be uninitialized, but we'll use it anyway
        memory_info = proc.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"run.py:1164","message":"get_process_metrics EXIT","data":{"pid":pid,"cpu_percent":cpu_percent,"memory_mb":memory_mb},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        return {"cpu_percent": cpu_percent, "memory_mb": memory_mb}
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"run.py:1168","message":"get_process_metrics EXCEPTION","data":{"pid":pid,"error":str(e)},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        return {"cpu_percent": None, "memory_mb": None}


def check_port_health(host: str, port: int, timeout: float = 0.2) -> Dict[str, any]:
    """Check health of a service by testing port latency.

    Args:
        host: Host to check
        port: Port to check
        timeout: Socket timeout in seconds (default 0.2 for faster response)

    Returns:
        Dict with 'available' (bool), 'latency_ms' (float or None), 'error' (str or None)
    """
    start_time = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)  # Reduced timeout for faster response
        result = sock.connect_ex((host, port))
        sock.close()
        latency_ms = (time.time() - start_time) * 1000

        if result == 0:
            return {"available": True, "latency_ms": latency_ms, "error": None}
        else:
            return {"available": False, "latency_ms": None, "error": "Connection refused"}
    except socket.timeout:
        return {"available": False, "latency_ms": None, "error": "Timeout"}
    except Exception as e:
        return {"available": False, "latency_ms": None, "error": str(e)}


def get_service_health(service_name: str, config: Dict, use_cache: bool = True, skip_port_check: bool = False) -> Dict:
    """Get comprehensive health metrics for a service.

    Args:
        service_name: Name of the service
        config: Configuration dict
        use_cache: If True, use cached health data if available and fresh
        skip_port_check: If True, skip port health checks (faster but less accurate)

    Returns:
        Dict with status, pid, cpu, memory, latency, and other metrics
    """
    # #region agent log
    import json
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"run.py:1205","message":"get_service_health ENTRY","data":{"service_name":service_name,"use_cache":use_cache,"skip_port_check":skip_port_check},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    # Check cache first
    current_time = time.time()
    if use_cache and service_name in _health_cache:
        cached_health, cache_time = _health_cache[service_name]
        if current_time - cache_time < _health_cache_ttl:
            # #region agent log
            try:
                with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"run.py:1219","message":"get_service_health CACHE HIT","data":{"service_name":service_name},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            return cached_health

    health = {
        "name": service_name,
        "status": "unknown",
        "pid": None,
        "cpu_percent": None,
        "memory_mb": None,
        "latency_ms": None,
        "port": None,
        "url": None,
        "error": None
    }

    # Get process info if available (fast check, no blocking)
    if service_name in _process_info:
        info = _process_info[service_name]
        process = info.get("process")
        pid = info.get("pid")

        if process:
            try:
                # Non-blocking poll check
                poll_result = process.poll()
                if poll_result is None:
                    health["status"] = "running"
                    health["pid"] = pid

                    # Get process metrics (non-blocking with cache)
                    if pid and PSUTIL_AVAILABLE:
                        metrics = get_process_metrics(pid, use_cache=True)
                        health["cpu_percent"] = metrics["cpu_percent"]
                        health["memory_mb"] = metrics["memory_mb"]
                else:
                    health["status"] = "stopped"
            except Exception:
                health["status"] = "unknown"

    # Get port and URL from config
    if service_name == "Backend":
        backend_config = config.get("backend", DEFAULT_CONFIG["backend"])
        health["port"] = backend_config.get("port", 8000)
        health["url"] = backend_config.get("health_url", "http://localhost:8000/healthz")

        # Check port health (with reduced timeout, or skip if requested)
        if skip_port_check:
            # #region agent log
            try:
                with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"run.py:1267","message":"get_service_health BEFORE test_port (Backend skip)","data":{"service_name":service_name,"port":health["port"]},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            # Just do a quick port test
            health["latency_ms"] = None
            port_result = test_port("localhost", health["port"])
            # #region agent log
            try:
                with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"run.py:1271","message":"get_service_health AFTER test_port (Backend skip)","data":{"service_name":service_name,"port":health["port"],"result":port_result},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            # If process is running but port is not available, verify with HTTP check
            if health["status"] == "running" and not port_result:
                # Try HTTP health check
                try:
                    from urllib.request import urlopen
                    start_time = time.time()
                    with urlopen(health["url"], timeout=1) as response:
                        if response.getcode() == 200:
                            port_result = True
                            health["latency_ms"] = (time.time() - start_time) * 1000
                        else:
                            # Process running but HTTP not OK
                            health["status"] = "degraded"
                            health["error"] = f"HTTP {response.getcode()}"
                except Exception as e:
                    # Port test failed and HTTP check failed, mark as unavailable
                    health["status"] = "unavailable"
                    health["error"] = f"Port/HTTP not responding: {str(e)[:50]}"
            elif not port_result:
                if health["status"] == "unknown":
                    health["status"] = "unavailable"
        else:
            port_health = check_port_health("localhost", health["port"], timeout=0.2)
            health["latency_ms"] = port_health.get("latency_ms")
            # If process is running but port check failed, try HTTP check
            if health["status"] == "running" and not port_health["available"]:
                try:
                    from urllib.request import urlopen
                    start_time = time.time()
                    with urlopen(health["url"], timeout=1) as response:
                        if response.getcode() == 200:
                            health["latency_ms"] = (time.time() - start_time) * 1000
                            port_health["available"] = True
                            port_health["error"] = None
                        else:
                            # Process running but HTTP not OK
                            health["status"] = "degraded"
                            health["error"] = f"HTTP {response.getcode()}"
                except Exception as e:
                    health["error"] = f"Port/HTTP check failed: {str(e)[:50]}"
                    health["status"] = "unavailable"
            elif not port_health["available"]:
                health["error"] = port_health.get("error")
                if health["status"] == "unknown":
                    health["status"] = "unavailable"

    elif service_name == "Frontend":
        frontend_config = config.get("frontend", DEFAULT_CONFIG["frontend"])
        health["port"] = frontend_config.get("port", 3000)
        health["url"] = frontend_config.get("url", "http://127.0.0.1:3000")

        # Check port health (with reduced timeout, or skip if requested)
        if skip_port_check:
            # #region agent log
            try:
                with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"run.py:1287","message":"get_service_health BEFORE test_port (Frontend skip)","data":{"service_name":service_name,"port":health["port"]},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            # Just do a quick port test
            health["latency_ms"] = None
            port_result = test_port("127.0.0.1", health["port"])
            # #region agent log
            try:
                with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"run.py:1291","message":"get_service_health AFTER test_port (Frontend skip)","data":{"service_name":service_name,"port":health["port"],"result":port_result},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            if not port_result:
                if health["status"] == "unknown":
                    health["status"] = "unavailable"
        else:
            port_health = check_port_health("127.0.0.1", health["port"], timeout=0.2)
            health["latency_ms"] = port_health.get("latency_ms")
            if not port_health["available"]:
                health["error"] = port_health.get("error")
                if health["status"] == "unknown":
                    health["status"] = "unavailable"

    # Cache the result
    _health_cache[service_name] = (health, current_time)

    return health


def add_error(message: str) -> None:
    """Add an error message to the global errors list."""
    _errors.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


def _log_reader_thread(log_file: Path, queue: Queue, stop_event: threading.Event) -> None:
    """Background thread that reads log file and puts lines into queue."""
    try:
        # Read existing content (last 50 lines)
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            for line in lines[-50:]:
                queue.put(line.rstrip())

        # Now tail the file
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(0, 2)  # Seek to end

            while not stop_event.is_set():
                line = f.readline()
                if line:
                    queue.put(line.rstrip())
                else:
                    time.sleep(0.2)  # Increased delay to reduce CPU usage
    except Exception as e:
        queue.put(f"[ERROR] Error leyendo logs: {e}")


def stream_combined_logs(backend_log: Path, frontend_log: Path) -> None:
    """Stream combined logs from backend and frontend with timestamps."""
    if not backend_log.exists() and not frontend_log.exists():
        console.print("[yellow][WARN] No hay archivos de log disponibles[/yellow]")
        return

    console.print(f"\n[cyan]Mostrando logs combinados (Ctrl+C para salir)...[/cyan]")
    console.print(f"[dim]Backend: {backend_log.name} | Frontend: {frontend_log.name}[/dim]\n")

    log_queue = Queue()
    stop_event = threading.Event()

    def read_log_file(log_file: Path, prefix: str):
        """Read a log file and prefix lines with service name."""
        try:
            if not log_file.exists():
                return

            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                for line in lines[-50:]:
                    log_queue.put(f"[{prefix}] {line.rstrip()}")

            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(0, 2)
                while not stop_event.is_set():
                    line = f.readline()
                    if line:
                        log_queue.put(f"[{prefix}] {line.rstrip()}")
                    else:
                        time.sleep(0.2)  # Increased delay to reduce CPU usage
        except Exception as e:
            log_queue.put(f"[ERROR] Error leyendo {prefix}: {e}")

    # Start threads for both logs
    threads = []
    if backend_log.exists():
        thread = Thread(target=read_log_file, args=(backend_log, "BACKEND"), daemon=True)
        thread.start()
        threads.append(thread)

    if frontend_log.exists():
        thread = Thread(target=read_log_file, args=(frontend_log, "FRONTEND"), daemon=True)
        thread.start()
        threads.append(thread)

    log_lines: List[str] = []
    max_lines = 100

    try:
        with Live(console=console, refresh_per_second=5, transient=False) as live:  # Reduced refresh rate
            while True:
                try:
                    while True:
                        line = log_queue.get_nowait()
                        log_lines.append(line)
                        if len(log_lines) > max_lines:
                            log_lines = log_lines[-max_lines:]
                except Empty:
                    pass

                if log_lines:
                    content = Text()
                    if len(log_lines) == max_lines:
                        content.append(f"[dim]... (mostrando últimas {max_lines} líneas) ...[/dim]\n", style="dim")

                    for line in log_lines:
                        # Color code by service
                        if line.startswith("[BACKEND]"):
                            content.append(line + "\n", style="cyan")
                        elif line.startswith("[FRONTEND]"):
                            content.append(line + "\n", style="magenta")
                        else:
                            content.append(line + "\n")

                    # Create nano-style layout
                    shortcuts = {"^X": "Salir", "^O": "Continuar"}
                    shortcuts_text = Text()
                    for key, desc in shortcuts.items():
                        shortcuts_text.append(f" {key} ", style="bold white on blue")
                        shortcuts_text.append(f"{desc}  ", style="white")

                    layout = Layout()
                    layout.split_column(
                        Layout(name="content", ratio=10),
                        Layout(name="shortcuts", size=1)
                    )

                    content_panel = Panel(
                        content,
                        title="[bold cyan]Logs Combinados[/bold cyan]",
                        border_style="cyan",
                        padding=(0, 1)
                    )
                    layout["content"].update(content_panel)

                    shortcuts_panel = Panel(
                        shortcuts_text,
                        border_style="blue",
                        box=box.ASCII
                    )
                    layout["shortcuts"].update(shortcuts_panel)

                    live.update(layout)

                time.sleep(0.2)  # Increased delay to reduce CPU usage

    except KeyboardInterrupt:
        stop_event.set()
        console.print("\n[yellow]Deteniendo visualización de logs combinados...[/yellow]")
    finally:
        stop_event.set()
        for thread in threads:
            thread.join(timeout=1)


def search_logs(log_file: Path, pattern: str) -> List[str]:
    """Search for a pattern in log file.

    Returns:
        List of matching lines
    """
    if not log_file.exists():
        return []

    matches = []
    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if re.search(pattern, line, re.IGNORECASE):
                    matches.append(line.rstrip())
    except Exception as e:
        console.print(f"[red][ERROR] Error buscando en logs: {e}[/red]")

    return matches


def filter_logs(log_file: Path, level: str) -> None:
    """Filter logs by level (INFO, ERROR, WARN, DEBUG).

    Shows filtered logs in real-time.
    """
    if not log_file.exists():
        console.print(f"[yellow][WARN] Archivo de log no encontrado: {log_file}[/yellow]")
        return

    level_patterns = {
        "ERROR": r"(?i)(error|exception|fail|failed)",
        "WARN": r"(?i)(warn|warning)",
        "INFO": r"(?i)(info|information)",
        "DEBUG": r"(?i)(debug|trace)"
    }

    pattern = level_patterns.get(level.upper())
    if not pattern:
        console.print(f"[yellow][WARN] Nivel desconocido: {level}[/yellow]")
        return

    console.print(f"\n[cyan]Filtrando logs por nivel: {level.upper()} (Ctrl+C para salir)...[/cyan]\n")

    log_queue = Queue()
    stop_event = threading.Event()

    def filter_reader():
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                for line in lines:
                    if re.search(pattern, line, re.IGNORECASE):
                        log_queue.put(line.rstrip())

            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(0, 2)
                while not stop_event.is_set():
                    line = f.readline()
                    if line and re.search(pattern, line, re.IGNORECASE):
                        log_queue.put(line.rstrip())
                    elif not line:
                        time.sleep(0.2)  # Increased delay to reduce CPU usage
        except Exception as e:
            log_queue.put(f"[ERROR] Error filtrando logs: {e}")

    thread = Thread(target=filter_reader, daemon=True)
    thread.start()

    log_lines: List[str] = []
    max_lines = 100

    try:
        with Live(console=console, refresh_per_second=5, transient=False) as live:  # Reduced refresh rate
            while True:
                try:
                    while True:
                        line = log_queue.get_nowait()
                        log_lines.append(line)
                        if len(log_lines) > max_lines:
                            log_lines = log_lines[-max_lines:]
                except Empty:
                    pass

                if log_lines:
                    content = Text()
                    for line in log_lines:
                        # Color by level
                        if re.search(level_patterns["ERROR"], line, re.IGNORECASE):
                            content.append(line + "\n", style="red")
                        elif re.search(level_patterns["WARN"], line, re.IGNORECASE):
                            content.append(line + "\n", style="yellow")
                        else:
                            content.append(line + "\n")

                    live.update(Panel(content, title=f"[cyan]Logs - {level.upper()}[/cyan]", border_style="cyan"))

                time.sleep(0.2)  # Increased delay to reduce CPU usage

    except KeyboardInterrupt:
        stop_event.set()
        console.print(f"\n[yellow]Deteniendo filtrado de logs...[/yellow]")
    finally:
        stop_event.set()
        thread.join(timeout=1)


def export_logs(log_file: Path, output_path: Path) -> None:
    """Export logs to a file."""
    if not log_file.exists():
        console.print(f"[yellow][WARN] Archivo de log no encontrado: {log_file}[/yellow]")
        return

    try:
        import shutil
        shutil.copy2(log_file, output_path)
        console.print(f"[green][OK] Logs exportados a: {output_path}[/green]")
    except Exception as e:
        console.print(f"[red][ERROR] Error exportando logs: {e}[/red]")


def clear_old_logs(logs_dir: Path, days: int = 7) -> None:
    """Clear log files older than specified days."""
    if not logs_dir.exists():
        return

    cutoff_time = time.time() - (days * 24 * 60 * 60)
    cleared = 0

    for log_file in logs_dir.glob("*.log"):
        try:
            if log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()
                cleared += 1
        except Exception:
            pass

    if cleared > 0:
        console.print(f"[green][OK] {cleared} archivo(s) de log antiguo(s) eliminado(s)[/green]")
    else:
        console.print("[dim]No hay archivos de log antiguos para eliminar[/dim]")


def stream_logs(log_file: Path, service_name: str) -> None:
    """Stream logs from a file in real-time using Rich Live for smooth updates.

    This is a TUI component that displays logs in real-time, similar to `tail -f`,
    but with better performance using threading and Rich Live updates.
    """
    if not log_file.exists():
        console.print(f"[yellow][WARN] Archivo de log no encontrado: {log_file}[/yellow]")
        return

    console.print(f"\n[cyan]Mostrando logs de {service_name} (Ctrl+C para salir)...[/cyan]")
    console.print(f"[dim]Archivo: {log_file}[/dim]\n")

    # Use Queue and Thread for non-blocking log reading
    log_queue = Queue()
    stop_event = threading.Event()

    # Start background thread to read logs
    reader_thread = Thread(
        target=_log_reader_thread,
        args=(log_file, log_queue, stop_event),
        daemon=True
    )
    reader_thread.start()

    # Collect lines for display
    log_lines: List[str] = []
    max_lines = 100  # Keep last 100 lines visible

    try:
        # Use Rich Live for smooth real-time updates (optimized refresh rate)
        with Live(console=console, refresh_per_second=5, transient=False) as live:
            while True:
                # Get new lines from queue (non-blocking)
                try:
                    while True:
                        line = log_queue.get_nowait()
                        log_lines.append(line)
                        # Keep only last max_lines
                        if len(log_lines) > max_lines:
                            log_lines = log_lines[-max_lines:]
                except Empty:
                    pass

                # Update display with nano-style viewer
                if log_lines:
                    # Show indicator if we're showing truncated content
                    content = Text()
                    if len(log_lines) == max_lines:
                        content.append(f"[dim]... (mostrando últimas {max_lines} líneas) ...[/dim]\n", style="dim")

                    for line in log_lines:
                        content.append(line + "\n")

                    # Create nano-style layout
                    shortcuts = {"^X": "Salir", "^O": "Continuar"}
                    shortcuts_text = Text()
                    for key, desc in shortcuts.items():
                        shortcuts_text.append(f" {key} ", style="bold white on blue")
                        shortcuts_text.append(f"{desc}  ", style="white")

                    # Create layout for nano style
                    layout = Layout()
                    layout.split_column(
                        Layout(name="content", ratio=10),
                        Layout(name="shortcuts", size=1)
                    )

                    # Content panel
                    content_panel = Panel(
                        content,
                        title=f"[bold cyan]{service_name} Logs[/bold cyan]",
                        border_style="cyan",
                        padding=(0, 1)
                    )
                    layout["content"].update(content_panel)

                    # Shortcuts bar (nano style)
                    shortcuts_panel = Panel(
                        shortcuts_text,
                        border_style="blue",
                        box=box.ASCII
                    )
                    layout["shortcuts"].update(shortcuts_panel)

                    live.update(layout)

                time.sleep(0.2)  # Increased delay to reduce CPU usage

    except KeyboardInterrupt:
        stop_event.set()
        console.print(f"\n[yellow]Deteniendo visualización de logs de {service_name}...[/yellow]")
    except Exception as e:
        stop_event.set()
        console.print(f"[red][ERROR] Error al mostrar logs: {e}[/red]")
    finally:
        stop_event.set()
        reader_thread.join(timeout=1)


def list_available_tests(project_root: Path) -> Dict:
    """List available test suites.

    Returns:
        Dict with test categories and their descriptions
    """
    return {
        "backend_unit": {
            "name": "Backend - Unit Tests",
            "description": "Tests unitarios del backend (pytest)",
            "path": "backend/tests/unit/",
            "command": ["uv", "run", "--extra", "dev", "pytest", "tests/unit/", "-v", "--tb=short", "-n", "4"]
        },
        "backend_integration": {
            "name": "Backend - Integration Tests",
            "description": "Tests de integración del backend (pytest)",
            "path": "backend/tests/integration/",
            "command": ["uv", "run", "--extra", "dev", "pytest", "tests/integration/", "-v", "--tb=short", "-n", "4"]
        },
        "frontend_unit": {
            "name": "Frontend - Unit Tests",
            "description": "Tests unitarios del frontend (vitest)",
            "path": "frontend/app/__tests__/unit/",
            "command": ["npm", "run", "test", "--", "--run"]
        },
        "frontend_e2e": {
            "name": "Frontend - E2E Tests",
            "description": "Tests end-to-end del frontend (playwright)",
            "path": "frontend/app/__tests__/e2e/",
            "command": ["npm", "run", "test:e2e"]
        },
        "all": {
            "name": "Todos los Tests",
            "description": "Ejecutar todos los tests (backend + frontend)",
            "path": "all",
            "command": None  # Special case, handled separately
        },
        "all_coverage": {
            "name": "Todos los Tests con Cobertura",
            "description": "Ejecutar todos los tests con reportes de cobertura",
            "path": "all",
            "command": None  # Special case, handled separately
        }
    }


def run_test_suite(test_type: str, project_root: Path, options: Dict) -> Dict:
    """Run a test suite.

    Args:
        test_type: Type of test (backend_unit, backend_integration, frontend_unit, frontend_e2e, all, all_coverage)
        project_root: Root directory of the project
        options: Additional options (coverage, workers, etc.)

    Returns:
        Dict with test results
    """
    tests = list_available_tests(project_root)

    if test_type not in tests:
        return {"success": False, "error": f"Tipo de test desconocido: {test_type}"}

    test_info = tests[test_type]
    start_time = time.time()

    console.print()
    console.print(Panel.fit(f"[cyan]{test_info['name']}[/cyan]", border_style="cyan"))
    console.print(f"[dim]{test_info['description']}[/dim]")
    console.print()

    # Handle special cases
    if test_type == "all":
        # Run all tests sequentially
        results = []
        for ttype in ["backend_unit", "backend_integration", "frontend_unit", "frontend_e2e"]:
            result = run_test_suite(ttype, project_root, options)
            results.append(result)
            if not result.get("success"):
                return {
                    "success": False,
                    "error": f"Fallo en {ttype}",
                    "results": results
                }
        return {"success": True, "results": results, "duration": time.time() - start_time}

    if test_type == "all_coverage":
        # Run all tests with coverage
        options["coverage"] = True
        return run_test_suite("all", project_root, options)

    # Get command and directory
    cmd = test_info["command"].copy()
    if not cmd:
        return {"success": False, "error": "Comando no disponible para este tipo de test"}

    # Determine working directory
    if test_type.startswith("backend"):
        cwd = project_root / "backend"
        # Add coverage if requested
        if options.get("coverage"):
            cmd.extend(["--cov=app", "--cov-report=term", "--cov-report=html"])
    elif test_type.startswith("frontend"):
        cwd = project_root / "frontend"
        if options.get("coverage"):
            # Frontend coverage handled by npm scripts
            pass
    else:
        cwd = project_root

    # Run the test
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Ejecutando {test_info['name']}...", total=None)

            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True
            )

            progress.update(task, completed=True)

        success = result.returncode == 0
        duration = time.time() - start_time

        # Store result in history
        test_result = {
            "test_type": test_type,
            "name": test_info["name"],
            "success": success,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "output": result.stdout,
            "error": result.stderr if not success else None
        }
        _test_results_history.append(test_result)

        # Show results
        if success:
            console.print(f"[green][OK] {test_info['name']} completado en {duration:.2f}s[/green]")
        else:
            console.print(f"[red][FAIL] {test_info['name']} falló después de {duration:.2f}s[/red]")
            if result.stderr:
                console.print(f"[red]Errores:[/red]")
                console.print(result.stderr[:500])  # Show first 500 chars

        return test_result

    except Exception as e:
        error_result = {
            "test_type": test_type,
            "name": test_info["name"],
            "success": False,
            "error": str(e),
            "duration": time.time() - start_time,
            "timestamp": datetime.now().isoformat()
        }
        _test_results_history.append(error_result)
        console.print(f"[red][ERROR] Error al ejecutar {test_info['name']}: {e}[/red]")
        return error_result


def show_test_results(results: Dict) -> None:
    """Display test results in a formatted way."""
    console.print()
    console.print(Panel.fit("[cyan]Resultados de Tests[/cyan]", border_style="cyan"))
    console.print()

    if results.get("success"):
        console.print(f"[green]✓ {results.get('name', 'Test')} - Exitoso[/green]")
        console.print(f"[dim]Duración: {results.get('duration', 0):.2f}s[/dim]")
    else:
        console.print(f"[red]✗ {results.get('name', 'Test')} - Falló[/red]")
        if results.get("error"):
            console.print(f"[red]Error: {results.get('error')}[/red]")

    console.print()


def show_test_menu(project_root: Path) -> None:
    """Show interactive test menu."""
    clear_screen()
    tests = list_available_tests(project_root)

    while True:
        console.print()
        console.print(Panel.fit("[cyan]Menú de Tests[/cyan]", border_style="cyan"))
        console.print()

        # Show test history if available
        if _test_results_history:
            console.print("[dim]Última ejecución:[/dim]")
            last_result = _test_results_history[-1]
            status_color = "green" if last_result.get("success") else "red"
            status_text = "✓" if last_result.get("success") else "✗"
            console.print(f"  [{status_color}]{status_text}[/{status_color}] {last_result.get('name')} - {last_result.get('duration', 0):.2f}s")
            console.print()

        # List available tests
        test_list = list(tests.items())
        console.print("[cyan]Tests disponibles:[/cyan]")
        for i, (key, test_info) in enumerate(test_list, 1):
            console.print(f"  [bold]{i}.[/bold] {test_info['name']}")
            console.print(f"      [dim]{test_info['description']}[/dim]")

        console.print(f"  [bold]{len(test_list) + 1}.[/bold] Ver historial de ejecuciones")
        console.print(f"  [bold]{len(test_list) + 2}.[/bold] Volver al menú principal")

        choice = safe_prompt_ask("\n[cyan]Selecciona una opción[/cyan]")
        if choice is None:
            break

        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(test_list):
                test_key = test_list[choice_num - 1][0]
                result = run_test_suite(test_key, project_root, {})
                show_test_results(result)
                safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
            elif choice_num == len(test_list) + 1:
                # Show test history
                console.print()
                console.print(Panel.fit("[cyan]Historial de Ejecuciones[/cyan]", border_style="cyan"))
                if _test_results_history:
                    table = Table(show_header=True, header_style="cyan")
                    table.add_column("Test", style="bold")
                    table.add_column("Estado", style="bold")
                    table.add_column("Duración", style="dim")
                    table.add_column("Fecha/Hora", style="dim")

                    for result in _test_results_history[-10:]:  # Show last 10
                        status = "✓" if result.get("success") else "✗"
                        status_color = "green" if result.get("success") else "red"
                        table.add_row(
                            result.get("name", "Unknown"),
                            f"[{status_color}]{status}[/{status_color}]",
                            f"{result.get('duration', 0):.2f}s",
                            result.get("timestamp", "")[:19]  # Truncate to date/time
                        )
                    console.print(table)
                else:
                    console.print("[yellow]No hay historial de ejecuciones[/yellow]")
                safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
            elif choice_num == len(test_list) + 2:
                break
            else:
                console.print("[yellow][WARN] Opción inválida[/yellow]")
        except ValueError:
            # Try to match by name
            matched = False
            for key, test_info in test_list:
                if choice.lower() in test_info["name"].lower():
                    result = run_test_suite(key, project_root, {})
                    show_test_results(result)
                    safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
                    matched = True
                    break
            if not matched:
                console.print("[yellow][WARN] Opción inválida[/yellow]")


def show_resource_usage() -> None:
    """Show system resource usage."""
    console.print()
    console.print(Panel.fit("[cyan]Uso de Recursos del Sistema[/cyan]", border_style="cyan"))
    console.print()

    if PSUTIL_AVAILABLE:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        console.print(f"[cyan]CPU:[/cyan] {cpu_percent}% ({cpu_count} cores)")

        # Memory usage
        memory = psutil.virtual_memory()
        memory_total_gb = memory.total / (1024 ** 3)
        memory_used_gb = memory.used / (1024 ** 3)
        memory_percent = memory.percent
        console.print(f"[cyan]Memoria:[/cyan] {memory_used_gb:.2f}GB / {memory_total_gb:.2f}GB ({memory_percent}%)")

        # Disk usage
        disk = psutil.disk_usage('/')
        disk_total_gb = disk.total / (1024 ** 3)
        disk_used_gb = disk.used / (1024 ** 3)
        disk_percent = disk.percent
        console.print(f"[cyan]Disco:[/cyan] {disk_used_gb:.2f}GB / {disk_total_gb:.2f}GB ({disk_percent}%)")
    else:
        console.print("[yellow][WARN] psutil no disponible. Instala psutil para ver métricas del sistema.[/yellow]")
        console.print("[dim]pip install psutil[/dim]")

    console.print()


def export_status_report(output_path: Path, project_root: Path, config: Dict) -> None:
    """Export a status report to a file."""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"AiutoX ERP - Reporte de Estado\n")
            f.write(f"Generado: {datetime.now().isoformat()}\n")
            f.write("=" * 50 + "\n\n")

            # Services status
            f.write("Servicios:\n")
            f.write("-" * 50 + "\n")
            for service_name in ["Backend", "Frontend"]:
                health = get_service_health(service_name, config)
                f.write(f"{service_name}:\n")
                f.write(f"  Estado: {health['status']}\n")
                f.write(f"  PID: {health['pid'] or 'N/A'}\n")
                if health['cpu_percent']:
                    f.write(f"  CPU: {health['cpu_percent']:.2f}%\n")
                if health['memory_mb']:
                    f.write(f"  Memoria: {health['memory_mb']:.2f}MB\n")
                if health['latency_ms']:
                    f.write(f"  Latencia: {health['latency_ms']:.2f}ms\n")
                f.write("\n")

            # Errors
            if _errors:
                f.write("Errores:\n")
                f.write("-" * 50 + "\n")
                for error in _errors:
                    f.write(f"{error}\n")
                f.write("\n")

            # Test history
            if _test_results_history:
                f.write("Historial de Tests:\n")
                f.write("-" * 50 + "\n")
                for result in _test_results_history[-10:]:
                    f.write(f"{result.get('name')}: {'OK' if result.get('success') else 'FAIL'} ({result.get('duration', 0):.2f}s)\n")

        console.print(f"[green][OK] Reporte exportado a: {output_path}[/green]")
    except Exception as e:
        console.print(f"[red][ERROR] Error exportando reporte: {e}[/red]")


def clear_all_logs(project_root: Path) -> None:
    """Clear all log files."""
    logs_dir = get_logs_dir(project_root)

    if not logs_dir.exists():
        console.print("[yellow][WARN] Directorio de logs no existe[/yellow]")
        return

    if Confirm.ask("[yellow]¿Estás seguro de que quieres eliminar todos los logs?[/yellow]"):
        cleared = 0
        for log_file in logs_dir.glob("*.log"):
            try:
                log_file.unlink()
                cleared += 1
            except Exception:
                pass

        console.print(f"[green][OK] {cleared} archivo(s) de log eliminado(s)[/green]")
    else:
        console.print("[dim]Operación cancelada[/dim]")


def show_service_details(service_name: str, config: Dict) -> None:
    """Show detailed information about a service."""
    clear_screen()
    console.print()
    console.print(Panel.fit(f"[cyan]Detalles de {service_name}[/cyan]", border_style="cyan"))
    console.print()

    health = get_service_health(service_name, config)

    table = Table(show_header=False, box=box.ASCII)
    table.add_column("Campo", style="bold cyan")
    table.add_column("Valor", style="white")

    table.add_row("Estado", health["status"])
    table.add_row("PID", str(health["pid"]) if health["pid"] else "N/A")

    if health["cpu_percent"] is not None:
        table.add_row("CPU", f"{health['cpu_percent']:.2f}%")
    else:
        table.add_row("CPU", "N/A")

    if health["memory_mb"] is not None:
        table.add_row("Memoria", f"{health['memory_mb']:.2f} MB")
    else:
        table.add_row("Memoria", "N/A")

    if health["port"]:
        table.add_row("Puerto", str(health["port"]))

    if health["url"]:
        table.add_row("URL", health["url"])

    if health["latency_ms"] is not None:
        table.add_row("Latencia", f"{health['latency_ms']:.2f} ms")
    else:
        table.add_row("Latencia", "N/A")

    if health["error"]:
        table.add_row("Error", f"[red]{health['error']}[/red]")

    console.print(table)
    console.print()


def clear_screen() -> None:
    """Clear the terminal screen using Rich console (optimized)."""
    console.clear()


def render_main_dashboard_with_layout(config: Dict, use_cache: bool = True, skip_port_checks: bool = False) -> Layout:
    """Render the main dashboard using Rich Layout for better organization.

    Optimized with caching and skip_port_checks for performance.

    Returns a Layout with:
    - Top: Service status table
    - Middle: Important URLs
    - Bottom: Menu options and shortcuts
    """
    # #region agent log
    import json
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"run.py:2249","message":"render_main_dashboard_with_layout ENTRY","data":{"config_keys":list(config.keys()) if config else None,"use_cache":use_cache,"skip_port_checks":skip_port_checks},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    # Get service health (with caching for performance)
    backend_health = get_service_health("Backend", config, use_cache=use_cache, skip_port_check=skip_port_checks)
    frontend_health = get_service_health("Frontend", config, use_cache=use_cache, skip_port_check=skip_port_checks)
    # #region agent log
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"run.py:2261","message":"render_main_dashboard_with_layout AFTER get_service_health","data":{"backend_health_keys":list(backend_health.keys()) if backend_health else None,"frontend_health_keys":list(frontend_health.keys()) if frontend_health else None},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion

    # Build service status table
    status_table = Table(show_header=True, header_style="bold cyan", box=box.ASCII, padding=(0, 1))
    status_table.add_column("Servicio", style="bold", width=18)
    status_table.add_column("Estado", style="bold", width=12)
    status_table.add_column("PID", width=8)
    status_table.add_column("Puerto", width=8)
    status_table.add_column("CPU/Mem", width=15)
    status_table.add_column("Latencia", width=10)

    # Status icons helper
    def get_status_icon(status: str) -> str:
        icons = {"running": "🟢", "degraded": "🟡", "stopped": "🔴", "unavailable": "⚪"}
        return icons.get(status, "⚪")

    # Backend row
    backend_status = backend_health["status"]
    status_color = "green" if backend_status == "running" else ("yellow" if backend_status == "degraded" else "red" if backend_status == "stopped" else "yellow")
    cpu_mem = "N/A"
    if backend_health["cpu_percent"] is not None and backend_health["memory_mb"] is not None:
        cpu_mem = f"{backend_health['cpu_percent']:.1f}% / {backend_health['memory_mb']:.0f}MB"
    latency = f"{backend_health['latency_ms']:.0f}ms" if backend_health["latency_ms"] is not None else "N/A"

    status_table.add_row(
        "Backend",
        f"{get_status_icon(backend_status)} [{status_color}]{backend_status}[/{status_color}]",
        str(backend_health["pid"]) if backend_health["pid"] else "N/A",
        str(backend_health.get("port", 8000)),
        cpu_mem,
        latency
    )

    # Frontend row
    frontend_status = frontend_health["status"]
    status_color = "green" if frontend_status == "running" else ("yellow" if frontend_status == "degraded" else "red" if frontend_status == "stopped" else "yellow")
    cpu_mem = "N/A"
    if frontend_health["cpu_percent"] is not None and frontend_health["memory_mb"] is not None:
        cpu_mem = f"{frontend_health['cpu_percent']:.1f}% / {frontend_health['memory_mb']:.0f}MB"
    latency = f"{frontend_health['latency_ms']:.0f}ms" if frontend_health["latency_ms"] is not None else "N/A"

    status_table.add_row(
        "Frontend",
        f"{get_status_icon(frontend_status)} [{status_color}]{frontend_status}[/{status_color}]",
        str(frontend_health["pid"]) if frontend_health["pid"] else "N/A",
        str(frontend_health.get("port", 3000)),
        cpu_mem,
        latency
    )

    # Docker services (quick check, no blocking)
    pg_config = DEFAULT_CONFIG["docker"]["postgres"]
    pg_running = check_container_running(pg_config["container"])
    docker_status = "running" if pg_running else "stopped"
    status_color = "green" if docker_status == "running" else "red"
    status_table.add_row(
        "Docker (PostgreSQL)",
        f"{get_status_icon(docker_status)} [{status_color}]{docker_status}[/{status_color}]",
        "-",
        str(pg_config["port"]),
        "-",
        "N/A"
    )

    # Build URLs panel
    backend_config = config.get("backend", DEFAULT_CONFIG["backend"])
    frontend_config = config.get("frontend", DEFAULT_CONFIG["frontend"])
    # #region agent log
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"run.py:2326","message":"render_main_dashboard_with_layout BEFORE URLs panel","data":{"backend_config":backend_config is not None,"frontend_config":frontend_config is not None,"backend_config_type":type(backend_config).__name__ if backend_config else None,"frontend_config_type":type(frontend_config).__name__ if frontend_config else None},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion

    # Ensure configs are not None
    if backend_config is None:
        backend_config = DEFAULT_CONFIG["backend"]
    if frontend_config is None:
        frontend_config = DEFAULT_CONFIG["frontend"]

    # #region agent log
    try:
        backend_port = backend_config.get('port', 8000) if isinstance(backend_config, dict) else 8000
        frontend_url = frontend_config.get('url', 'http://127.0.0.1:3000') if isinstance(frontend_config, dict) else 'http://127.0.0.1:3000'
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"run.py:2335","message":"render_main_dashboard_with_layout URL values","data":{"backend_port":backend_port,"frontend_url":frontend_url,"backend_port_is_none":backend_port is None,"frontend_url_is_none":frontend_url is None},"timestamp":int(time.time()*1000)})+"\n")
    except Exception as e:
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"run.py:2337","message":"render_main_dashboard_with_layout URL values ERROR","data":{"error":str(e)},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
    # #endregion

    urls_text = Text()
    urls_text.append("🌐 URLs Importantes:\n\n", style="bold cyan")
    urls_text.append(f"  Frontend:     ", style="dim")
    frontend_url = frontend_config.get('url', 'http://127.0.0.1:3000') if isinstance(frontend_config, dict) else 'http://127.0.0.1:3000'
    urls_text.append(f"{frontend_url}\n", style="bold blue")
    urls_text.append(f"  Backend API:  ", style="dim")
    backend_port = backend_config.get('port', 8000) if isinstance(backend_config, dict) else 8000
    urls_text.append(f"http://localhost:{backend_port}\n", style="bold blue")
    urls_text.append(f"  API Docs:     ", style="dim")
    urls_text.append(f"http://localhost:{backend_port}/docs\n", style="bold blue")
    urls_text.append(f"  pgAdmin:      ", style="dim")
    urls_text.append("http://localhost:8888\n", style="bold blue")

    # Create layout
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )

    layout["body"].split_row(
        Layout(name="status", ratio=2),
        Layout(name="urls", ratio=1)
    )

    # Header
    header_text = Text()
    header_text.append("╭", style="cyan")
    header_text.append("─" * 58, style="cyan")
    header_text.append("╮\n", style="cyan")
    header_text.append("│", style="cyan")
    header_text.append("  AiutoX ERP - Control Suite", style="bold cyan")
    header_text.append(" " * 28, style="cyan")
    header_text.append("│\n", style="cyan")
    header_text.append("╰", style="cyan")
    header_text.append("─" * 58, style="cyan")
    header_text.append("╯", style="cyan")
    layout["header"].update(Panel(header_text, border_style="cyan"))

    # Status panel
    layout["status"].update(Panel(status_table, title="[bold cyan]Estado de Servicios[/bold cyan]", border_style="cyan"))

    # URLs panel
    layout["urls"].update(Panel(urls_text, title="[bold cyan]URLs[/bold cyan]", border_style="cyan"))

    # Footer (will be updated by menu)
    footer_text = Text()
    footer_text.append("[dim]💡 Presiona 'Q' o '15' y Enter para salir, Ctrl+C para salir inmediatamente[/dim]", style="dim")
    layout["footer"].update(Panel(footer_text, border_style="dim"))

    # #region agent log
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"run.py:2378","message":"render_main_dashboard_with_layout BEFORE return","data":{"layout_created":layout is not None},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion

    return layout


def show_nano_style_viewer(content: Text, title: str, shortcuts: Dict[str, str] = None, refresh_rate: float = 5.0) -> None:
    """Display content in a nano-style viewer with shortcuts at the bottom.

    Optimized with controlled refresh rate to avoid CPU overload.

    Args:
        content: Text content to display
        title: Title for the viewer
        shortcuts: Dict of shortcut keys and descriptions (e.g., {"^X": "Salir", "^F": "Buscar"})
        refresh_rate: Maximum refresh rate per second (default 5.0 to avoid CPU overload)
    """
    if shortcuts is None:
        shortcuts = {"^X": "Salir", "^O": "Continuar"}

    # Build shortcuts bar (like nano) - optimized rendering
    shortcuts_text = Text()
    for key, desc in shortcuts.items():
        shortcuts_text.append(f" {key} ", style="bold white on blue")
        shortcuts_text.append(f"{desc}  ", style="white")

    # Create layout
    layout = Layout()
    layout.split_column(
        Layout(name="content", ratio=10),
        Layout(name="shortcuts", size=1)
    )

    # Content panel
    content_panel = Panel(
        content,
        title=f"[bold cyan]{title}[/bold cyan]",
        border_style="cyan",
        padding=(0, 1)
    )
    layout["content"].update(content_panel)

    # Shortcuts bar (nano style)
    shortcuts_panel = Panel(
        shortcuts_text,
        border_style="blue",
        box=box.ASCII
    )
    layout["shortcuts"].update(shortcuts_panel)

    console.print(layout)


def render_dashboard(config: Dict, use_cache: bool = True, skip_port_checks: bool = False) -> Table:
    """Render the enhanced dashboard with real-time metrics.

    Args:
        config: Configuration dict
        use_cache: If True, use cached health data for faster rendering
        skip_port_checks: If True, skip port health checks (fastest, but less accurate)

    Returns:
        Table object with dashboard data
    """
    # #region agent log
    import json
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"run.py:2037","message":"render_dashboard ENTRY","data":{"use_cache":use_cache,"skip_port_checks":skip_port_checks},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    # Get health for all services (with caching for performance)
    # For faster rendering, we can skip port checks if skip_port_checks is True
    # #region agent log
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"run.py:2049","message":"render_dashboard BEFORE get_service_health Backend","data":{},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    backend_health = get_service_health("Backend", config, use_cache=use_cache, skip_port_check=skip_port_checks)
    # #region agent log
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"run.py:2051","message":"render_dashboard AFTER get_service_health Backend","data":{},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    # #region agent log
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"run.py:2052","message":"render_dashboard BEFORE get_service_health Frontend","data":{},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    frontend_health = get_service_health("Frontend", config, use_cache=use_cache, skip_port_check=skip_port_checks)
    # #region agent log
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"run.py:2054","message":"render_dashboard AFTER get_service_health Frontend","data":{},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion

    # If skip_port_checks, don't do port health checks (much faster)
    if skip_port_checks:
        # Just use process status, no port checks
        if backend_health.get("status") == "running" and backend_health.get("latency_ms") is None:
            backend_health["latency_ms"] = 0  # Assume OK if process is running
        if frontend_health.get("status") == "running" and frontend_health.get("latency_ms") is None:
            frontend_health["latency_ms"] = 0  # Assume OK if process is running

    # Create dashboard table
    table = Table(show_header=True, header_style="cyan", title="[cyan]AiutoX ERP - Control Suite[/cyan]")
    table.add_column("Servicio", style="bold")
    table.add_column("PID", style="dim")
    table.add_column("Estado", style="bold")
    table.add_column("CPU/Mem", style="dim")
    table.add_column("Latencia", style="dim")

    # Backend row
    if backend_health["status"] == "running":
        status_color = "green"
    elif backend_health["status"] == "degraded":
        status_color = "yellow"
    elif backend_health["status"] == "stopped":
        status_color = "red"
    else:
        status_color = "yellow"
    cpu_mem = "N/A"
    if backend_health["cpu_percent"] is not None and backend_health["memory_mb"] is not None:
        cpu_mem = f"{backend_health['cpu_percent']:.1f}% / {backend_health['memory_mb']:.0f}MB"
    latency = f"{backend_health['latency_ms']:.0f}ms" if backend_health["latency_ms"] is not None else "N/A"

    table.add_row(
        "Backend",
        str(backend_health["pid"]) if backend_health["pid"] else "N/A",
        f"[{status_color}]{backend_health['status']}[/{status_color}]",
        cpu_mem,
        latency
    )

    # Frontend row
    if frontend_health["status"] == "running":
        status_color = "green"
    elif frontend_health["status"] == "degraded":
        status_color = "yellow"
    elif frontend_health["status"] == "stopped":
        status_color = "red"
    else:
        status_color = "yellow"
    cpu_mem = "N/A"
    if frontend_health["cpu_percent"] is not None and frontend_health["memory_mb"] is not None:
        cpu_mem = f"{frontend_health['cpu_percent']:.1f}% / {frontend_health['memory_mb']:.0f}MB"
    latency = f"{frontend_health['latency_ms']:.0f}ms" if frontend_health["latency_ms"] is not None else "N/A"

    table.add_row(
        "Frontend",
        str(frontend_health["pid"]) if frontend_health["pid"] else "N/A",
        f"[{status_color}]{frontend_health['status']}[/{status_color}]",
        cpu_mem,
        latency
    )

    # Docker services (check cache for this too, or skip if requested)
    pg_config = DEFAULT_CONFIG["docker"]["postgres"]
    if skip_port_checks:
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"run.py:2099","message":"render_dashboard BEFORE test_port Docker","data":{"port":pg_config["port"]},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        # Just check if port is open quickly without full health check
        pg_available = test_port("localhost", pg_config["port"])
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"run.py:2102","message":"render_dashboard AFTER test_port Docker","data":{"port":pg_config["port"],"available":pg_available},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        pg_status = "running" if pg_available else "stopped"
        pg_latency = "N/A"
    else:
        cache_key = f"Docker_PostgreSQL_{pg_config['port']}"
        current_time = time.time()

        if use_cache and cache_key in _health_cache:
            cached_health, cache_time = _health_cache[cache_key]
            if current_time - cache_time < _health_cache_ttl:
                pg_health = cached_health
            else:
                pg_health = check_port_health("localhost", pg_config["port"], timeout=0.2)
                _health_cache[cache_key] = (pg_health, current_time)
        else:
            pg_health = check_port_health("localhost", pg_config["port"], timeout=0.2)
            _health_cache[cache_key] = (pg_health, current_time)

        pg_status = "running" if pg_health["available"] else "stopped"
        pg_latency = f"{pg_health['latency_ms']:.0f}ms" if pg_health["latency_ms"] else "N/A"

    table.add_row("Docker (PostgreSQL)", "-", f"[{'green' if pg_status == 'running' else 'red'}]{pg_status}[/{'green' if pg_status == 'running' else 'red'}]", "-", pg_latency)

    # #region agent log
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"run.py:2112","message":"render_dashboard EXIT","data":{},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    return table


def _show_shortcuts_help() -> None:
    """Show help for keyboard shortcuts."""
    console.print()
    console.print(Panel.fit("[cyan]Atajos de Teclado[/cyan]", border_style="cyan"))
    console.print()

    shortcuts = [
        ("1-9", "Acciones rápidas del menú"),
        ("B", "Ver logs del Backend"),
        ("F", "Ver logs del Frontend"),
        ("L", "Ver logs combinados"),
        ("S", "Estado de servicios"),
        ("T", "Menú de Tests"),
        ("R", "Reiniciar servicio seleccionado"),
        ("K", "Detener servicio seleccionado"),
        ("X", "Matar servicio seleccionado"),
        ("C", "Limpiar logs"),
        ("E", "Ver errores"),
        ("H", "Ayuda (este menú)"),
        ("Q", "Salir"),
        ("Ctrl+C", "Salir con confirmación"),
        ("Esc", "Volver al menú principal"),
    ]

    table = Table(show_header=True, header_style="cyan")
    table.add_column("Atajo", style="bold cyan")
    table.add_column("Acción", style="white")

    for shortcut, action in shortcuts:
        table.add_row(shortcut, action)

    console.print(table)
    console.print()


def _handle_keypress(key: str) -> Optional[str]:
    """Handle keyboard shortcut.

    Returns:
        Action string or None if no action
    """
    key_upper = key.upper()

    shortcuts = {
        "B": "logs_backend",
        "F": "logs_frontend",
        "L": "logs_combined",
        "S": "status",
        "T": "tests",
        "R": "restart",
        "K": "stop",
        "X": "kill",
        "C": "clear_logs",
        "E": "errors",
        "H": "help",
        "Q": "exit",
    }

    return shortcuts.get(key_upper)


def safe_prompt_ask(prompt: str, default: str = "") -> Optional[str]:
    """Safely ask for user input, handling EOF and non-interactive terminals.

    Args:
        prompt: Prompt text
        default: Default value if user just presses Enter

    Returns:
        User input or None if EOF/non-interactive
    """
    if not sys.stdin.isatty():
        return None

    try:
        return Prompt.ask(prompt, default=default)
    except (EOFError, KeyboardInterrupt):
        return None
    except Exception:
        return None


def _setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        console.print("\n[yellow]Interrupción recibida. Cerrando...[/yellow]")
        _stop_log_streaming.set()
        sys.exit(0)

    # Handle Ctrl+C (SIGINT) and SIGTERM
    if platform.system() != "Windows":
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    else:
        # Windows uses different signal handling
        signal.signal(signal.SIGINT, signal_handler)


def show_interactive_menu(project_root: Path, config: Dict) -> None:
    """Show interactive menu for viewing logs and errors.

    This is a TUI menu that allows users to interactively manage services,
    view logs in real-time, and monitor errors. Supports keyboard shortcuts.
    """
    _setup_signal_handlers()
    global _current_menu_state, _selected_service

    # Menu options with shortcuts
    options = [
        ("Ver logs del Backend", "logs_backend", "B"),
        ("Ver logs del Frontend", "logs_frontend", "F"),
        ("Ver logs combinados", "logs_combined", "L"),
        ("Ver estado de servicios", "status", "S"),
        ("Menú de Tests", "tests", "T"),
        ("Reiniciar servicio", "restart", "R"),
        ("Detener servicio", "stop", "K"),
        ("Matar servicio", "kill", "X"),
        ("Ver errores", "errors", "E"),
        ("Limpiar logs", "clear_logs", "C"),
        ("Uso de recursos", "resources", None),
        ("Exportar reporte", "export_report", None),
        ("Detalles de servicio", "service_details", None),
        ("Ayuda (Shortcuts)", "help", "H"),
        ("Salir", "exit", "Q"),
    ]

    # Clear screen and show initial dashboard (skip port checks for faster startup)
    clear_screen()
    # #region agent log
    import json
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"run.py:2236","message":"show_interactive_menu BEFORE render_dashboard","data":{},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    dashboard_layout = render_main_dashboard_with_layout(config, use_cache=False, skip_port_checks=True)
    # #region agent log
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"run.py:2239","message":"show_interactive_menu AFTER render_dashboard","data":{},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    # #region agent log
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"run.py:2725","message":"show_interactive_menu BEFORE console.print layout","data":{"dashboard_layout":dashboard_layout is not None,"layout_type":type(dashboard_layout).__name__ if dashboard_layout else None},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    try:
        console.print(dashboard_layout)
    except Exception as e:
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"run.py:2730","message":"show_interactive_menu console.print layout EXCEPTION","data":{"error":str(e),"error_type":type(e).__name__},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        raise
    console.print()

    first_iteration = True
    while True:
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"run.py:2242","message":"show_interactive_menu LOOP ITERATION START","data":{},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion

        # Refresh dashboard on each iteration (except first, already shown)
        if not first_iteration:
            dashboard_layout = render_main_dashboard_with_layout(config, use_cache=True, skip_port_checks=True)
            console.print(dashboard_layout)
            console.print()
        first_iteration = False

        # Show errors if any (quick check, no blocking)
        if _errors:
            error_panel = Panel.fit(
                f"[red]Errores ({len(_errors)})[/red]\n" + "\n".join(_errors[-5:]),
                border_style="red"
            )
            console.print(error_panel)
            console.print()

        # Show shortcuts hint
        console.print("[dim]Atajos: [B]ackend [F]rontend [L]ogs [S]tatus [T]ests [R]estart [K]ill [E]rrors [H]elp [Q]uit[/dim]")
        console.print()

        # Menu options
        console.print("[cyan]Opciones:[/cyan]")
        for i, (label, action, shortcut) in enumerate(options, 1):
            shortcut_text = f" [{shortcut}]" if shortcut else ""
            console.print(f"  [bold]{i}.[/bold] {label}{shortcut_text}")

        # Get user input (support shortcuts)
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"run.py:2263","message":"show_interactive_menu BEFORE Prompt.ask","data":{"stdin_available":sys.stdin.isatty()},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion

        # Check if stdin is available (interactive terminal)
        if not sys.stdin.isatty():
            console.print("[yellow][WARN] Terminal no interactivo detectado. Saliendo...[/yellow]")
            break

        choice = safe_prompt_ask("\n[cyan]Selecciona una opción[/cyan]", default=str(len(options)))
        if choice is None:
            # EOF or non-interactive terminal
            console.print("\n[yellow]Saliendo del menú...[/yellow]")
            break

        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"run.py:2280","message":"show_interactive_menu AFTER Prompt.ask","data":{"choice":choice},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion

        # Handle shortcuts
        action = None
        shortcut_action = _handle_keypress(choice)
        if shortcut_action:
            action = shortcut_action
        else:
            # Try numeric input
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(options):
                    action = options[choice_num - 1][1]
                else:
                    console.print("[yellow][WARN] Opción inválida[/yellow]")
                    continue
            except ValueError:
                # Try to match by name
                for label, act, _ in options:
                    if choice.lower() in label.lower():
                        action = act
                        break
                if not action:
                    console.print("[yellow][WARN] Opción inválida[/yellow]")
                    continue

        # Execute action
        if action == "exit":
            if Confirm.ask("[yellow]¿Estás seguro de que quieres salir?[/yellow]"):
                console.print("\n[cyan]Saliendo del menú interactivo...[/cyan]")
                # Stop all services gracefully before exiting
                stop_all_services()
                break
        elif action == "logs_backend":
            clear_screen()
            log_file = _log_files.get("backend")
            if log_file:
                stream_logs(log_file, "Backend")
            else:
                console.print("[yellow][WARN] No hay archivo de log para el Backend[/yellow]")
                safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
            clear_screen()
        elif action == "logs_frontend":
            clear_screen()
            log_file = _log_files.get("frontend")
            if log_file:
                stream_logs(log_file, "Frontend")
            else:
                console.print("[yellow][WARN] No hay archivo de log para el Frontend[/yellow]")
                safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
            clear_screen()
        elif action == "logs_combined":
            clear_screen()
            backend_log = _log_files.get("backend")
            frontend_log = _log_files.get("frontend")
            if backend_log or frontend_log:
                stream_combined_logs(
                    backend_log or Path("/dev/null"),
                    frontend_log or Path("/dev/null")
                )
            else:
                console.print("[yellow][WARN] No hay archivos de log disponibles[/yellow]")
                safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
            clear_screen()
        elif action == "errors":
            clear_screen()
            if _errors:
                console.print()
                console.print(Panel.fit(f"[red]Todos los Errores ({len(_errors)})[/red]", border_style="red"))
                for error in _errors:
                    console.print(f"  {error}")
            else:
                console.print("[green][OK] No hay errores registrados[/green]")
            safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
            clear_screen()
        elif action == "status":
            clear_screen()
            # Show full status with refreshed dashboard
            console.print()
            dashboard_layout = render_main_dashboard_with_layout(config, use_cache=False)  # Force refresh
            console.print(dashboard_layout)
            console.print()
            show_summary(False, False, False, config)
            safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
            clear_screen()
        elif action == "tests":
            clear_screen()
            show_test_menu(project_root)
            clear_screen()
        elif action == "restart":
            clear_screen()
            # Select service
            if not _process_info:
                console.print("[yellow][WARN] No hay servicios corriendo[/yellow]")
                safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
                continue

            service_list = list(_process_info.keys())
            console.print("\n[cyan]Selecciona servicio a reiniciar:[/cyan]")
            for i, svc in enumerate(service_list, 1):
                console.print(f"  {i}. {svc}")

            choice = safe_prompt_ask("", default="1")
            if choice is None:
                console.print("[yellow]Operación cancelada[/yellow]")
                continue
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(service_list):
                    restart_service(service_list[idx], project_root, config)
                else:
                    console.print("[yellow][WARN] Opción inválida[/yellow]")
            except ValueError:
                console.print("[yellow][WARN] Opción inválida[/yellow]")
            safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
            clear_screen()
        elif action == "stop":
            clear_screen()
            if not _process_info:
                console.print("[yellow][WARN] No hay servicios corriendo[/yellow]")
                safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
                continue

            service_list = list(_process_info.keys())
            console.print("\n[cyan]Selecciona servicio a detener:[/cyan]")
            for i, svc in enumerate(service_list, 1):
                console.print(f"  {i}. {svc}")

            choice = safe_prompt_ask("", default="1")
            if choice is None:
                console.print("[yellow]Operación cancelada[/yellow]")
                continue
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(service_list):
                    stop_service(service_list[idx], graceful=True)
                else:
                    console.print("[yellow][WARN] Opción inválida[/yellow]")
            except ValueError:
                console.print("[yellow][WARN] Opción inválida[/yellow]")
            safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
            clear_screen()
        elif action == "kill":
            clear_screen()
            if not _process_info:
                console.print("[yellow][WARN] No hay servicios corriendo[/yellow]")
                safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
                continue

            if Confirm.ask("[red]¿Estás seguro de que quieres matar el servicio?[/red]"):
                service_list = list(_process_info.keys())
                console.print("\n[cyan]Selecciona servicio a matar:[/cyan]")
                for i, svc in enumerate(service_list, 1):
                    console.print(f"  {i}. {svc}")

                choice = safe_prompt_ask("", default="1")
            if choice is None:
                console.print("[yellow]Operación cancelada[/yellow]")
                continue
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(service_list):
                        kill_service(service_list[idx])
                    else:
                        console.print("[yellow][WARN] Opción inválida[/yellow]")
                except ValueError:
                    console.print("[yellow][WARN] Opción inválida[/yellow]")
            safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
            clear_screen()
        elif action == "clear_logs":
            clear_screen()
            clear_all_logs(project_root)
            safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
            clear_screen()
        elif action == "resources":
            clear_screen()
            show_resource_usage()
            safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
            clear_screen()
        elif action == "export_report":
            clear_screen()
            output_path = project_root / ".logs" / f"status_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            export_status_report(output_path, project_root, config)
            safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
            clear_screen()
        elif action == "service_details":
            clear_screen()
            service_list = ["Backend", "Frontend"]
            console.print("\n[cyan]Selecciona servicio:[/cyan]")
            for i, svc in enumerate(service_list, 1):
                console.print(f"  {i}. {svc}")

            choice = safe_prompt_ask("", default="1")
            if choice is None:
                console.print("[yellow]Operación cancelada[/yellow]")
                clear_screen()
                continue
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(service_list):
                    show_service_details(service_list[idx], config)
                else:
                    console.print("[yellow][WARN] Opción inválida[/yellow]")
            except ValueError:
                console.print("[yellow][WARN] Opción inválida[/yellow]")
            safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
            clear_screen()
        elif action == "help":
            clear_screen()
            _show_shortcuts_help()
            safe_prompt_ask("[dim]Presiona Enter para continuar...[/dim]", default="")
            clear_screen()


def _start_all_services(
    skip_docker: bool = False,
    skip_backend: bool = False,
    skip_frontend: bool = False,
    run_tests: bool = False,
    force: bool = False,
) -> None:
    """Internal function to start all services."""
    # #region agent log
    import json
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:2611","message":"_start_all_services ENTRY","data":{"skip_docker":skip_docker,"skip_backend":skip_backend,"skip_frontend":skip_frontend},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    console.print()
    console.print(Panel.fit("[cyan]AiutoX ERP - Inicio Completo[/cyan]", border_style="cyan"))
    console.print()

    # Get project root
    current_file = Path(__file__).resolve()
    # Calculate project_root: backend/scripts/cli/commands/run.py -> go up 5 levels to project root
    # run.py -> commands/ -> cli/ -> scripts/ -> backend/ -> project_root/
    project_root = current_file.parent.parent.parent.parent.parent
    # #region agent log
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:2627","message":"_start_all_services project_root calculated","data":{"project_root":str(project_root)},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion

    backend_dir = project_root / "backend"
    frontend_dir = project_root / "frontend"

    # Verify directories exist
    if not backend_dir.exists():
        console.print(f"[red][ERROR] Directorio backend no encontrado: {backend_dir}[/red]")
        raise typer.Exit(1)

    if not frontend_dir.exists():
        console.print(f"[red][ERROR] Directorio frontend no encontrado: {frontend_dir}[/red]")
        raise typer.Exit(1)

    # Load environment configuration
    # #region agent log
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:2642","message":"_start_all_services BEFORE load_env_config","data":{},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    config = load_env_config(project_root)
    # #region agent log
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:2643","message":"_start_all_services AFTER load_env_config","data":{},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion

    # Start Docker
    if not skip_docker:
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:2645","message":"_start_all_services BEFORE start_docker_services","data":{},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        if not start_docker_services(backend_dir):
            console.print("[red][ERROR] Error al iniciar servicios Docker[/red]")
            # #region agent log
            try:
                with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:2736","message":"_start_all_services Docker FAILED, raising Exit","data":{},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            raise typer.Exit(1)
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:2649","message":"_start_all_services AFTER start_docker_services","data":{},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
    else:
        console.print("[yellow][WARN] Saltando inicio de servicios Docker (--skip-docker)[/yellow]")

    # Start Backend
    if not skip_backend:
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:2653","message":"_start_all_services BEFORE start_backend","data":{},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        try:
            backend_started = start_backend(backend_dir, config.get("backend"), project_root=project_root, force=force)
            if not backend_started:
                console.print("[yellow][WARN] Backend no se pudo iniciar correctamente[/yellow]")
                console.print("[yellow]       El proceso continuará, pero verifica los errores arriba[/yellow]")
                add_error("Backend no se pudo iniciar correctamente")
        except Exception as e:
            console.print(f"[red][ERROR] Excepción al iniciar backend: {e}[/red]")
            console.print("[yellow][WARN] Continuando con el proceso...[/yellow]")
            add_error(f"Backend: Excepción - {str(e)}")
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:2665","message":"_start_all_services AFTER start_backend","data":{},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
    else:
        console.print("[yellow][WARN] Saltando inicio del backend (--skip-backend)[/yellow]")

    # Start Frontend
    if not skip_frontend:
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:2670","message":"_start_all_services BEFORE start_frontend","data":{},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        try:
            frontend_started = start_frontend(frontend_dir, config.get("frontend"), project_root=project_root, force=force)
            if not frontend_started:
                console.print("[yellow][WARN] Frontend no se pudo iniciar correctamente[/yellow]")
                console.print("[yellow]       El proceso continuará, pero verifica los errores arriba[/yellow]")
                add_error("Frontend no se pudo iniciar correctamente")
        except Exception as e:
            console.print(f"[red][ERROR] Excepción al iniciar frontend: {e}[/red]")
            console.print("[yellow][WARN] Continuando con el proceso...[/yellow]")
            add_error(f"Frontend: Excepción - {str(e)}")
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:2682","message":"_start_all_services AFTER start_frontend","data":{},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
    else:
        console.print("[yellow][WARN] Saltando inicio del frontend (--skip-frontend)[/yellow]")

    # Show summary
    # #region agent log
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:2687","message":"_start_all_services BEFORE show_summary","data":{},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    show_summary(skip_docker, skip_backend, skip_frontend, config)
    # #region agent log
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:2689","message":"_start_all_services AFTER show_summary","data":{},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion

    # Run tests if requested
    if run_tests:
        console.print()
        console.print(Panel.fit("[cyan]PASO 5: Ejecutar Tests E2E[/cyan]", border_style="cyan"))
        console.print()

        console.print("[cyan]Esperando a que todos los servicios estén completamente listos...[/cyan]")
        time.sleep(5)

        console.print("[cyan]Ejecutando tests E2E de Playwright (modo no headless)...[/cyan]")
        console.print()

        result = subprocess.run(
            ["npx", "playwright", "test", "--project=chromium", "--headed"],
            cwd=frontend_dir,
        )

        if result.returncode == 0:
            console.print("[green][OK] Tests E2E pasaron correctamente[/green]")
        else:
            console.print("[yellow][WARN] Algunos tests E2E fallaron. Revisa los resultados arriba.[/yellow]")

    console.print()
    console.print(Panel.fit("[green][OK] Proceso completado[/green]", border_style="green"))
    console.print()

    # Show errors summary if any
    if _errors:
        console.print()
        console.print(Panel.fit(f"[yellow]Errores Encontrados ({len(_errors)})[/yellow]", border_style="yellow"))
        for error in _errors:
            console.print(f"  {error}")
        console.print()

    # Show interactive menu (only if stdin is available and no critical errors)
    # #region agent log
    import json
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:2806","message":"_start_all_services BEFORE show_interactive_menu","data":{"stdin_available":sys.stdin.isatty(),"has_errors":len(_errors)},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion

    # Only show interactive menu if stdin is available (interactive terminal)
    if sys.stdin.isatty():
        console.print("[cyan]Iniciando menú interactivo...[/cyan]")
        console.print("[dim]Puedes ver logs en tiempo real y gestionar los servicios desde aquí[/dim]")
        console.print("[dim]💡 Presiona 'Q' o '15' y Enter para salir del menú[/dim]")
        console.print()
        try:
            show_interactive_menu(project_root, config)
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Menú cerrado[/yellow]")
        except Exception as e:
            # #region agent log
            import json
            import traceback
            try:
                with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:3270","message":"show_interactive_menu EXCEPTION","data":{"error":str(e),"error_type":type(e).__name__,"traceback":traceback.format_exc()},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            console.print(f"[red][ERROR] Error en menú interactivo: {e}[/red]")
    else:
        console.print("[yellow][WARN] Terminal no interactivo. Menú no disponible.[/yellow]")
        console.print("[yellow]       Usa un terminal interactivo para acceder al menú.[/yellow]")
    # #region agent log
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:2510","message":"_start_all_services AFTER show_interactive_menu","data":{},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion


@app.command()
def serv(
    skip_docker: bool = typer.Option(False, "--skip-docker", help="Skip Docker services"),
    skip_backend: bool = typer.Option(False, "--skip-backend", help="Skip backend server"),
    skip_frontend: bool = typer.Option(False, "--skip-frontend", help="Skip frontend server"),
    run_tests: bool = typer.Option(False, "--tests", help="Run E2E tests after starting services"),
    force: bool = typer.Option(False, "--force", help="Force restart services if they are already running"),
):
    """Start all development services (Docker, Backend, Frontend)."""
    _start_all_services(skip_docker, skip_backend, skip_frontend, run_tests, force=force)


@app.command()
def dev(
    all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Start all development services (Docker, Backend, Frontend)",
    ),
    skip_docker: bool = typer.Option(False, "--skip-docker", help="Skip Docker services"),
    skip_backend: bool = typer.Option(False, "--skip-backend", help="Skip backend server"),
    skip_frontend: bool = typer.Option(False, "--skip-frontend", help="Skip frontend server"),
    run_tests: bool = typer.Option(False, "--tests", help="Run E2E tests after starting services"),
    docker_test: bool = typer.Option(False, "--docker-test", help="Test connections to Docker containers (PostgreSQL and Redis)"),
    backend: bool = typer.Option(False, "--backend", help="Start only the backend server"),
    frontend: bool = typer.Option(False, "--frontend", help="Start only the frontend server"),
    force: bool = typer.Option(False, "--force", help="Force restart services if they are already running"),
):
    """Start development services."""
    # #region agent log
    import json
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:2752","message":"dev() ENTRY","data":{"all":all,"skip_docker":skip_docker,"skip_backend":skip_backend,"skip_frontend":skip_frontend},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    console.print()
    console.print(Panel.fit("[cyan]AiutoX ERP - Inicio Completo[/cyan]", border_style="cyan"))
    console.print()

    # Get project root
    current_file = Path(__file__).resolve()
    # Calculate project_root: backend/scripts/cli/commands/run.py -> go up 5 levels to project root
    # run.py -> commands/ -> cli/ -> scripts/ -> backend/ -> project_root/
    project_root = current_file.parent.parent.parent.parent.parent

    backend_dir = project_root / "backend"
    frontend_dir = project_root / "frontend"

    # Verify directories exist
    if not backend_dir.exists():
        console.print(f"[red][ERROR] Directorio backend no encontrado: {backend_dir}[/red]")
        raise typer.Exit(1)

    if not frontend_dir.exists():
        console.print(f"[red][ERROR] Directorio frontend no encontrado: {frontend_dir}[/red]")
        raise typer.Exit(1)

    # Load environment configuration
    config = load_env_config(project_root)

    # Handle docker-test option
    if docker_test:
        test_docker_connections()
        return

    # Handle backend-only option
    if backend and not all:
        start_backend(backend_dir, config.get("backend"), force=force)
        console.print()
        console.print(Panel.fit("[green][OK] Backend iniciado[/green]", border_style="green"))
        console.print()
        return

    # Handle frontend-only option
    if frontend and not all:
        start_frontend(frontend_dir, config.get("frontend"), force=force)
        console.print()
        console.print(Panel.fit("[green][OK] Frontend iniciado[/green]", border_style="green"))
        console.print()
        return

    # Start services
    if all:
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:2816","message":"dev() BEFORE _start_all_services","data":{},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        _start_all_services(skip_docker, skip_backend, skip_frontend, run_tests, force=force)
        # #region agent log
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"run.py:2818","message":"dev() AFTER _start_all_services","data":{},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
    else:
        console.print("[yellow]Opciones disponibles:[/yellow]")
        console.print("  [cyan]--all[/cyan]          Iniciar todos los servicios (Docker, Backend, Frontend)")
        console.print("  [cyan]--backend[/cyan]       Iniciar solo el backend")
        console.print("  [cyan]--frontend[/cyan]      Iniciar solo el frontend")
        console.print("  [cyan]--docker-test[/cyan]   Probar conexiones con contenedores Docker")
        console.print()
        console.print("Ejemplos:")
        console.print("  [cyan]aiutox run dev --all[/cyan]")
        console.print("  [cyan]aiutox run dev --backend[/cyan]")
        console.print("  [cyan]aiutox run dev --frontend[/cyan]")
        console.print("  [cyan]aiutox run dev --docker-test[/cyan]")
