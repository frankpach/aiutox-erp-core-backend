#!/usr/bin/env python3
"""Script de diagnóstico para probar componentes del sistema de desarrollo por partes."""

import sys
import time
import json
from pathlib import Path

# Setup logging
debug_log_path = Path(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log")
debug_log_path.parent.mkdir(parents=True, exist_ok=True)

def log(message, location, data=None):
    """Log a message."""
    try:
        with open(debug_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "diagnostic",
                "hypothesisId": "DIAG",
                "location": location,
                "message": message,
                "data": data or {},
                "timestamp": int(time.time() * 1000)
            }) + "\n")
    except Exception as e:
        print(f"Error logging: {e}")

print("=" * 60)
print("DIAGNÓSTICO DEL SISTEMA DE DESARROLLO")
print("=" * 60)
print()

# Test 1: Import básico
log("TEST 1: Import básico START", "test_run_debug.py:25")
print("[TEST 1] Probando imports básicos...")
try:
    import os
    import sys
    import subprocess
    import time
    import socket
    print("  [OK] Imports basicos OK")
    log("TEST 1: Import basico SUCCESS", "test_run_debug.py:32")
except Exception as e:
    print(f"  [ERROR] Error en imports basicos: {e}")
    log("TEST 1: Import básico FAIL", "test_run_debug.py:35", {"error": str(e)})
    sys.exit(1)

# Test 2: Import de módulos del CLI
log("TEST 2: Import CLI modules START", "test_run_debug.py:39")
print("[TEST 2] Probando import de módulos CLI...")
try:
    from scripts.cli.commands import run
    print("  [OK] Import de run.py OK")
    log("TEST 2: Import CLI modules SUCCESS", "test_run_debug.py:43")
except Exception as e:
    print(f"  [ERROR] Error importando run.py: {e}")
    log("TEST 2: Import CLI modules FAIL", "test_run_debug.py:46", {"error": str(e)})
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Función test_port
log("TEST 3: test_port function START", "test_run_debug.py:52")
print("[TEST 3] Probando función test_port...")
try:
    result = run.test_port("localhost", 8000, timeout=0.5)
    print(f"  [OK] test_port OK (resultado: {result})")
    log("TEST 3: test_port function SUCCESS", "test_run_debug.py:56", {"result": result})
except Exception as e:
    print(f"  [ERROR] Error en test_port: {e}")
    log("TEST 3: test_port function FAIL", "test_run_debug.py:59", {"error": str(e)})
    import traceback
    traceback.print_exc()

# Test 4: Función get_process_metrics (si psutil disponible)
log("TEST 4: get_process_metrics START", "test_run_debug.py:64")
print("[TEST 4] Probando función get_process_metrics...")
try:
    if run.PSUTIL_AVAILABLE:
        # Probar con el PID actual
        import os
        current_pid = os.getpid()
        metrics = run.get_process_metrics(current_pid, use_cache=True)
        print(f"  [OK] get_process_metrics OK (CPU: {metrics.get('cpu_percent')}, Mem: {metrics.get('memory_mb')})")
        log("TEST 4: get_process_metrics SUCCESS", "test_run_debug.py:71", {"metrics": metrics})
    else:
        print("  [SKIP] psutil no disponible, saltando test")
        log("TEST 4: get_process_metrics SKIP", "test_run_debug.py:74", {"reason": "psutil not available"})
except Exception as e:
    print(f"  [ERROR] Error en get_process_metrics: {e}")
    log("TEST 4: get_process_metrics FAIL", "test_run_debug.py:77", {"error": str(e)})
    import traceback
    traceback.print_exc()

# Test 5: Función get_service_health (sin servicios corriendo)
log("TEST 5: get_service_health START", "test_run_debug.py:82")
print("[TEST 5] Probando función get_service_health...")
try:
    from scripts.cli.commands.run import DEFAULT_CONFIG
    config = {"backend": DEFAULT_CONFIG["backend"], "frontend": DEFAULT_CONFIG["frontend"]}
    health = run.get_service_health("Backend", config, use_cache=False, skip_port_check=True)
    print(f"  [OK] get_service_health OK (status: {health.get('status')})")
    log("TEST 5: get_service_health SUCCESS", "test_run_debug.py:87", {"health": health})
except Exception as e:
    print(f"  [ERROR] Error en get_service_health: {e}")
    log("TEST 5: get_service_health FAIL", "test_run_debug.py:90", {"error": str(e)})
    import traceback
    traceback.print_exc()

# Test 6: Función render_dashboard
log("TEST 6: render_dashboard START", "test_run_debug.py:95")
print("[TEST 6] Probando función render_dashboard...")
try:
    from scripts.cli.commands.run import DEFAULT_CONFIG
    config = {"backend": DEFAULT_CONFIG["backend"], "frontend": DEFAULT_CONFIG["frontend"]}
    table = run.render_dashboard(config, use_cache=False, skip_port_checks=True)
    print(f"  [OK] render_dashboard OK")
    log("TEST 6: render_dashboard SUCCESS", "test_run_debug.py:101")
except Exception as e:
    print(f"  [ERROR] Error en render_dashboard: {e}")
    log("TEST 6: render_dashboard FAIL", "test_run_debug.py:104", {"error": str(e)})
    import traceback
    traceback.print_exc()

# Test 7: Función show_interactive_menu (solo setup, no loop)
log("TEST 7: show_interactive_menu setup START", "test_run_debug.py:109")
print("[TEST 7] Probando setup de show_interactive_menu...")
try:
    from scripts.cli.commands.run import DEFAULT_CONFIG
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent  # backend/
    config = {"backend": DEFAULT_CONFIG["backend"], "frontend": DEFAULT_CONFIG["frontend"]}

    # Solo probar el setup, no el loop completo
    run._setup_signal_handlers()
    print("  [OK] Setup de show_interactive_menu OK")
    log("TEST 7: show_interactive_menu setup SUCCESS", "test_run_debug.py:118")
except Exception as e:
    print(f"  [ERROR] Error en setup de show_interactive_menu: {e}")
    log("TEST 7: show_interactive_menu setup FAIL", "test_run_debug.py:121", {"error": str(e)})
    import traceback
    traceback.print_exc()

# Test 8: Import de typer y rich
log("TEST 8: Import typer/rich START", "test_run_debug.py:126")
print("[TEST 8] Probando imports de typer y rich...")
try:
    import typer
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    console = Console()
    print("  [OK] Imports de typer/rich OK")
    log("TEST 8: Import typer/rich SUCCESS", "test_run_debug.py:133")
except Exception as e:
    print(f"  [ERROR] Error en imports de typer/rich: {e}")
    log("TEST 8: Import typer/rich FAIL", "test_run_debug.py:136", {"error": str(e)})
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("DIAGNÓSTICO COMPLETADO")
print(f"Logs guardados en: {debug_log_path}")
print("=" * 60)

















