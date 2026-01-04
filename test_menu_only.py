#!/usr/bin/env python3
"""Script para probar solo el menú interactivo sin iniciar servicios."""

import sys
import json
import time
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
                "runId": "menu-test",
                "hypothesisId": "MENU",
                "location": location,
                "message": message,
                "data": data or {},
                "timestamp": int(time.time() * 1000)
            }) + "\n")
    except Exception as e:
        print(f"Error logging: {e}")

print("=" * 60)
print("PRUEBA DEL MENU INTERACTIVO (SIN SERVICIOS)")
print("=" * 60)
print()

log("TEST MENU: START", "test_menu_only.py:30")

# Import
try:
    from scripts.cli.commands.run import show_interactive_menu, DEFAULT_CONFIG
    log("TEST MENU: Import SUCCESS", "test_menu_only.py:34")
except Exception as e:
    print(f"[ERROR] Error importando: {e}")
    log("TEST MENU: Import FAIL", "test_menu_only.py:37", {"error": str(e)})
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Setup
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent  # backend/ -> project_root/
config = {
    "backend": DEFAULT_CONFIG["backend"],
    "frontend": DEFAULT_CONFIG["frontend"]
}

print(f"Project root: {project_root}")
print(f"Config loaded: {bool(config)}")
print()
print("[INFO] Iniciando menu interactivo...")
print("[INFO] Presiona 'Q' y Enter para salir")
print()

log("TEST MENU: BEFORE show_interactive_menu", "test_menu_only.py:54", {"project_root": str(project_root)})

try:
    show_interactive_menu(project_root, config)
    log("TEST MENU: AFTER show_interactive_menu (returned)", "test_menu_only.py:58")
    print()
    print("[OK] Menu cerrado correctamente")
except KeyboardInterrupt:
    log("TEST MENU: KeyboardInterrupt", "test_menu_only.py:62")
    print()
    print("[INFO] Interrumpido por usuario (Ctrl+C)")
except Exception as e:
    log("TEST MENU: EXCEPTION", "test_menu_only.py:66", {"error": str(e)})
    print(f"[ERROR] Excepcion en menu: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("PRUEBA COMPLETADA")
print(f"Logs en: {debug_log_path}")
print("=" * 60)

















