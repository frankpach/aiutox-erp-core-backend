#!/usr/bin/env python3
"""
Script para diagnosticar problemas de imports en el backend.
Identifica módulos que causan el cuelgue del servidor.
"""

import importlib
import sys
import traceback
from pathlib import Path

# Agregar el directorio backend al path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))


def test_import(module_name: str) -> tuple[bool, str]:
    """Intenta importar un módulo y devuelve el resultado."""
    try:
        importlib.import_module(module_name)
        return True, "OK"
    except Exception as e:
        return False, f"ERROR: {e}\n{traceback.format_exc()}"


def main():
    """Diagnóstico completo de imports."""
    print("🔍 DIAGNÓSTICO DE IMPORTS DEL BACKEND")
    print("=" * 50)

    # Lista de módulos críticos del API v1
    critical_modules = [
        "app.api.v1.activities",
        "app.api.v1.activity_icons",
        "app.api.v1.approvals",
        "app.api.v1.auth",
        "app.api.v1.automation",
        "app.api.v1.comments",
        "app.api.v1.config",
        "app.api.v1.contact_methods",
        "app.api.v1.files",
        "app.api.v1.flow_runs",
        "app.api.v1.folders",
        "app.api.v1.import_export",
        "app.api.v1.integrations",
        "app.api.v1.notifications",
        "app.api.v1.preferences",
        "app.api.v1.pubsub",
        "app.api.v1.reporting",
        "app.api.v1.search",
        "app.api.v1.sse",
        "app.api.v1.tags",
        "app.api.v1.templates",
        "app.api.v1.users",
        "app.api.v1.views",
        "app.api.v1.workflows",
        # Módulos de características
        "app.features.tasks.statuses",
        # Módulos del sistema modular
        "app.modules.calendar.api",
        "app.modules.crm.api",
        "app.modules.inventory.api",
        "app.modules.products.api",
        "app.modules.tasks.api",
    ]

    # Probar imports básicos primero
    print("\n📦 IMPORTS BÁSICOS")
    print("-" * 30)
    basic_modules = [
        "app.core.config_file",
        "app.core.db.session",
        "app.core.exceptions",
        "app.api.v1",
    ]

    for module in basic_modules:
        success, result = test_import(module)
        status = "✅" if success else "❌"
        print(f"{status} {module}: {result}")

    # Probar imports críticos
    print("\n🚨 IMPORTS CRÍTICOS")
    print("-" * 30)
    failed_modules = []

    for module in critical_modules:
        success, result = test_import(module)
        status = "✅" if success else "❌"
        print(f"{status} {module}")
        if not success:
            failed_modules.append((module, result))

    # Probar el import completo del API router
    print("\n🔗 IMPORT COMPLETO API ROUTER")
    print("-" * 30)
    try:
        print("✅ app.api.v1.api_router: OK")
    except Exception as e:
        print(f"❌ app.api.v1.api_router: ERROR: {e}")
        print(f"Traceback:\n{traceback.format_exc()}")

    # Probar el import del main
    print("\n🎯 IMPORT DEL MAIN")
    print("-" * 30)
    try:
        print("✅ app.main: OK")
    except Exception as e:
        print(f"❌ app.main: ERROR: {e}")
        print(f"Traceback:\n{traceback.format_exc()}")

    # Resumen
    print("\n📊 RESUMEN")
    print("-" * 30)
    total = len(critical_modules)
    failed = len(failed_modules)
    passed = total - failed

    print(f"Total módulos críticos: {total}")
    print(f"✅ Exitosos: {passed}")
    print(f"❌ Fallidos: {failed}")

    if failed_modules:
        print("\n🔍 MÓDULOS CON ERRORES:")
        for module, error in failed_modules:
            print(f"\n❌ {module}:")
            print(f"   {error}")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
